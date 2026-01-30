import json
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
import frappe
from tap_lms.feedback_handler.audio_creation import generate_feedback_audio


class FeedbackProcessor:
    """
    Handles message parsing/validation and all DB updates for feedback processing.
    
    """

    def parse_and_validate(self, body: bytes) -> Tuple[Dict[str, Any], str]:
        try:
            message_data = json.loads(body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}") from e

        submission_id = message_data.get("submission_id")
        if not submission_id:
            raise ValueError("Missing submission_id in message")

        if not message_data.get("feedback"):
            raise ValueError("Missing feedback data in message")

        return message_data, submission_id

    def ensure_submission_exists(self, submission_id: str) -> None:
        # Preserve the existing (odd) behavior: commit and re-check in case another txn created it.
        if frappe.db.exists("ImgSubmission", submission_id):
            return

        frappe.logger().error(f"ImgSubmission {submission_id} not found. Commiting DB.")
        frappe.db.commit()

        if not frappe.db.exists("ImgSubmission", submission_id):
            raise ValueError(f"ImgSubmission {submission_id} not found")

    def is_retryable_error(self, error: Exception) -> bool:
        error_str = str(error).lower()

        non_retryable_patterns = [
            "does not exist",
            "not found",
            "invalid",
            "permission denied",
            "duplicate",
            "constraint violation",
            "missing submission_id",
            "missing feedback data",
            "validation error",
        ]

        return not any(pattern in error_str for pattern in non_retryable_patterns)

    def mark_submission_failed(self, submission_id: str, error_message: str) -> None:
        try:
            submission = frappe.get_doc("ImgSubmission", submission_id)
            submission.status = "Failed"

            if hasattr(submission, "error_message"):
                submission.error_message = error_message[:500]

            submission.save(ignore_permissions=True)
            frappe.logger().error(f"Marked submission {submission_id} as failed: {error_message}")
        except Exception as e:
            frappe.logger().error(
                f"Error marking submission {submission_id} as failed: {str(e)}"
            )

    def update_submission(self, message_data: Dict[str, Any]) -> None:
        submission_id = message_data["submission_id"]
        feedback_data = message_data.get("feedback", {})
        plagiarism_data = feedback_data.get("plagiarism_output", {})

        submission = frappe.get_doc("ImgSubmission", submission_id)

        # Extract plagiarism data
        is_plagiarized = plagiarism_data.get("is_plagiarized", False)
        is_ai_generated = plagiarism_data.get("is_ai_generated", False)
        match_type = plagiarism_data.get("match_type", "original")
        plagiarism_source = plagiarism_data.get("plagiarism_source", "none")
        similarity_score = plagiarism_data.get("similarity_score", 0.0)
        ai_detection_source = plagiarism_data.get("ai_detection_source")
        ai_confidence = plagiarism_data.get("ai_confidence", 0.0)
        similar_sources = plagiarism_data.get("similar_sources", [])

        plagiarism_status = self._determine_plagiarism_status(
            is_plagiarized, is_ai_generated, match_type, plagiarism_source
        )
        result_status = self._determine_result_status(is_plagiarized, is_ai_generated)
        grade = self._extract_grade(feedback_data, submission_id)

        strengths = feedback_data.get("strengths", [])
        strengths_message = "\n".join([f"• {strength}" for strength in strengths])

        areas_for_improvement = feedback_data.get("areas_for_improvement", [])
        areas_for_improvement_message = "\n".join(
            [f"• {area}" for area in areas_for_improvement]
        )

        learning_objectives_feedback = feedback_data.get("learning_objectives_feedback", [])
        learning_objectives_feedback_message = "\n".join(
            [f"• {objective}" for objective in learning_objectives_feedback]
        )

        rubric_evaluations = feedback_data.get("rubric_evaluations", [])
        rubric_evaluations_rows = []
        for rubric in rubric_evaluations:
            rubric_evaluations_rows.append(
                {
                    "skill": rubric.get("Skill", ""),
                    "grade_value": float(rubric.get("grade_value", 0)),
                    "observation": rubric.get("observation", ""),
                }
            )


        # Extract translated feedback and language
        overall_feedback_translated = feedback_data.get("overall_feedback_translated", "")
        translation_language = feedback_data.get("translation_language", "")
    
        # Generate audio feedback if translated text and language are provided
        audio_feedback_url = ""
        if overall_feedback_translated and translation_language:
            try:
                frappe.logger().info(
                    f"Generating audio feedback for submission {submission_id} "
                    f"in language {translation_language}"
                )

                audio_feedback_url = generate_feedback_audio(
                    text=overall_feedback_translated,
                    language_name=translation_language,
                    submission_id=submission_id,
                    tone=None
                )

                frappe.logger().info(
                    f"Audio feedback generated successfully for submission {submission_id}: {audio_feedback_url}"
                )
            except Exception as e:
                frappe.logger().error(
                    f"Failed to generate audio feedback for submission {submission_id}: {str(e)}"
                )
                # Continue without audio - don't fail the entire submission update
                audio_feedback_url = ""

        update_data = {
            "status": "Completed",
            "result_status": result_status,
            "completed_at": datetime.now(),
            # Plagiarism fields
            "plagiarism_status": plagiarism_status,
            "is_plagiarized": is_plagiarized,
            "match_type": match_type,
            "plagiarism_source": plagiarism_source,
            "similarity_score": similarity_score * 100,
            "similar_sources": json.dumps(similar_sources),
            # AI detection fields
            "is_ai_generated": is_ai_generated,
            "ai_detection_source": ai_detection_source or "",
            "ai_confidence": ai_confidence * 100,
            # Feedback fields
            "grade": grade,
            "overall_feedback": feedback_data.get("overall_feedback", ""),
            "overall_feedback_translated": feedback_data.get("overall_feedback_translated", ""),
            "translation_language": feedback_data.get("translation_language", ""),
            "audio_feedback_url": audio_feedback_url,
            "generated_feedback": json.dumps(feedback_data, indent=2, ensure_ascii=False),
            "learning_objectives_feedback": learning_objectives_feedback_message,
            "strengths": strengths_message,
            "areas_for_improvement": areas_for_improvement_message,
            "encouragement": feedback_data.get("encouragement", ""),
            # Child table field
            "rubric_evaluations": rubric_evaluations_rows,
            "plagiarism_result": message_data.get("plagiarism_score", 0),
        }

        submission.update(update_data)
        submission.save(ignore_permissions=True)

    def _determine_result_status(self, is_plagiarized: bool, is_ai_generated: bool) -> str:
        if is_plagiarized or is_ai_generated:
            return "Success - Flagged"
        return "Success - Original"

    def _determine_plagiarism_status(
        self,
        is_plagiarized: bool,
        is_ai_generated: bool,
        match_type: str,
        plagiarism_source: str,
    ) -> str:
        if is_ai_generated:
            return "Flagged - AI Generated"

        if not is_plagiarized:
            if match_type == "resubmission_allowed":
                return "Resubmission Allowed"
            return "Original"

        status_map = {
            "exact_duplicate": "Flagged - Exact Match",
            "near_duplicate": "Flagged - Near Duplicate",
            "semantic_match": "Flagged - Semantic Match",
        }
        if match_type in status_map:
            return status_map[match_type]

        if plagiarism_source in ["peer", "peer_collusion"]:
            return "Flagged - Peer Plagiarism"
        if plagiarism_source in ["self_cross_assignment", "self_late_resubmission"]:
            return "Flagged - Self Plagiarism"

        return "Flagged - Exact Match"

    def _extract_grade(self, feedback_data: Dict[str, Any], submission_id: str) -> float:
        grade_recommendation: Any = feedback_data.get("final_grade", "50")

        try:
            if isinstance(grade_recommendation, str):
                grade_clean = "".join(
                    c for c in grade_recommendation if c.isdigit() or c == "."
                )
                grade = float(grade_clean) if grade_clean else 0.0
            else:
                grade = float(grade_recommendation)
        except (ValueError, TypeError):
            grade = 0.0
            frappe.logger().warning(
                f"Could not parse grade '{grade_recommendation}' for submission {submission_id}, using 0.0"
            )

        return grade


