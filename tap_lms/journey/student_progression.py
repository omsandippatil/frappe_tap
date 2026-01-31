# -*- coding: utf-8 -*-
# Copyright (c) 2025, TAP LMS
# File: tap_lms/journey/student_progression.py
#
# Student Progression API for self-paced learning
#
# APIs:
# - get_next_content: Get next content item for student
# - mark_content_complete: Mark content as completed  
# - get_student_progress: Get student's overall progress
#
# Endpoints:
# - /api/method/tap_lms.journey.student_progression.get_next_content
# - /api/method/tap_lms.journey.student_progression.mark_content_complete
# - /api/method/tap_lms.journey.student_progression.get_student_progress

import frappe
from frappe import _
from frappe.utils import now_datetime, cint, flt
import json

# ============================================================
# CONSTANTS
# ============================================================

TIER_BY_WEEK = {
    1: "Basic",
    2: "Intermediate",
    # Week 3+ defaults to "Advanced"
}

DEFAULT_TIER = "Advanced"  # For week 3+
REMEDIAL_TIER = "Remedial"

VALID_CONTENT_TYPES = ["VideoClass", "Quiz", "Assignment", "NoteContent", "CourseProject"]


# ============================================================
# TIER DETERMINATION
# ============================================================

def get_tier_for_week(week_no: int) -> str:
    """
    Determine the default tier based on week number.
    
    Args:
        week_no: Week/Stage number (1, 2, 3, ...)
    
    Returns:
        str: "Basic", "Intermediate", or "Advanced"
    """
    week_no = cint(week_no)
    return TIER_BY_WEEK.get(week_no, DEFAULT_TIER)


# ============================================================
# STUDENT PROGRESS MANAGEMENT
# ============================================================

def get_or_create_student_progress(student_id: str, course_level: str) -> dict:
    """
    Get existing progress record or create a new one.
    
    Args:
        student_id: Student document ID
        course_level: Course Level document ID
    
    Returns:
        dict: StudentStageProgress record as dictionary
    """
    # Try to find existing progress
    existing = frappe.db.get_value(
        "StudentStageProgress",
        {
            "student": student_id,
            "course_context": course_level,
            "stage_type": "LearningUnit"
        },
        [
            "name", "student", "stage", "status", "current_week", "current_tier",
            "current_content_index", "is_on_remedial", "remedial_attempts",
            "performance_metrics", "start_timestamp", "last_activity_timestamp"
        ],
        as_dict=True
    )
    
    if existing:
        return existing
    
    # Create new progress record
    # Find first LU for Week 1, Basic tier
    first_lu = get_first_learning_unit(course_level, week_no=1, tier="Basic")
    
    if not first_lu:
        frappe.throw(
            _("No Learning Unit found for Week 1 Basic tier in Course Level {0}").format(course_level)
        )
    
    # Create new StudentStageProgress
    progress_doc = frappe.new_doc("StudentStageProgress")
    progress_doc.student = student_id
    progress_doc.stage_type = "LearningUnit"
    progress_doc.stage = first_lu
    progress_doc.course_context = course_level
    progress_doc.status = "assigned"
    progress_doc.current_week = 1
    progress_doc.current_tier = "Basic"
    progress_doc.current_content_index = 0
    progress_doc.is_on_remedial = 0
    progress_doc.remedial_attempts = 0
    progress_doc.start_timestamp = now_datetime()
    progress_doc.last_activity_timestamp = now_datetime()
    progress_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    
    return {
        "name": progress_doc.name,
        "student": progress_doc.student,
        "stage": progress_doc.stage,
        "status": progress_doc.status,
        "current_week": progress_doc.current_week,
        "current_tier": progress_doc.current_tier,
        "current_content_index": progress_doc.current_content_index,
        "is_on_remedial": progress_doc.is_on_remedial,
        "remedial_attempts": progress_doc.remedial_attempts,
        "performance_metrics": None,
        "start_timestamp": progress_doc.start_timestamp,
        "last_activity_timestamp": progress_doc.last_activity_timestamp
    }


def update_student_progress(progress_name: str, updates: dict):
    """
    Update StudentStageProgress fields.
    
    Args:
        progress_name: StudentStageProgress document name
        updates: Dictionary of field: value pairs to update
    """
    progress_doc = frappe.get_doc("StudentStageProgress", progress_name)
    
    for field, value in updates.items():
        if hasattr(progress_doc, field):
            setattr(progress_doc, field, value)
    
    progress_doc.last_activity_timestamp = now_datetime()
    progress_doc.save(ignore_permissions=True)
    frappe.db.commit()


# ============================================================
# LEARNING UNIT QUERIES
# ============================================================

def get_first_learning_unit(course_level: str, week_no: int, tier: str) -> str:
    """
    Get the first LearningUnit for a given week and tier.
    
    Args:
        course_level: Course Level ID
        week_no: Week/Stage number
        tier: Difficulty tier (Basic/Intermediate/Advanced/Remedial)
    
    Returns:
        str: LearningUnit ID or None
    """
    result = frappe.db.sql("""
        SELECT 
            lu.name as learning_unit
        FROM `tabLearningUnitList` lul
        INNER JOIN `tabLearningUnit` lu ON lu.name = lul.learning_unit
        WHERE lul.parent = %(course_level)s
          AND lul.parenttype = 'Course Level'
          AND lul.week_no = %(week_no)s
          AND lu.difficulty_tier = %(tier)s
        ORDER BY lul.idx ASC
        LIMIT 1
    """, {
        "course_level": course_level,
        "week_no": cint(week_no),
        "tier": tier
    }, as_dict=True)
    
    return result[0].learning_unit if result else None


def get_next_learning_unit(course_level: str, week_no: int, tier: str, after_lu: str) -> str:
    """
    Get the next LearningUnit after the current one (same week, same tier).
    
    Args:
        course_level: Course Level ID
        week_no: Week/Stage number
        tier: Difficulty tier
        after_lu: Current LearningUnit ID
    
    Returns:
        str: Next LearningUnit ID or None
    """
    # Get current LU's position (idx)
    current_idx = frappe.db.get_value(
        "LearningUnitList",
        {
            "parent": course_level,
            "parenttype": "Course Level",
            "learning_unit": after_lu
        },
        "idx"
    )
    
    if current_idx is None:
        return None
    
    # Find next LU with higher idx, same week, same tier
    result = frappe.db.sql("""
        SELECT 
            lu.name as learning_unit
        FROM `tabLearningUnitList` lul
        INNER JOIN `tabLearningUnit` lu ON lu.name = lul.learning_unit
        WHERE lul.parent = %(course_level)s
          AND lul.parenttype = 'Course Level'
          AND lul.week_no = %(week_no)s
          AND lu.difficulty_tier = %(tier)s
          AND lul.idx > %(current_idx)s
        ORDER BY lul.idx ASC
        LIMIT 1
    """, {
        "course_level": course_level,
        "week_no": cint(week_no),
        "tier": tier,
        "current_idx": current_idx
    }, as_dict=True)
    
    return result[0].learning_unit if result else None


def check_week_exists(course_level: str, week_no: int) -> bool:
    """
    Check if any learning units exist for a given week.
    
    Args:
        course_level: Course Level ID
        week_no: Week number
    
    Returns:
        bool: True if week exists
    """
    count = frappe.db.count(
        "LearningUnitList",
        {
            "parent": course_level,
            "parenttype": "Course Level",
            "week_no": cint(week_no)
        }
    )
    return count > 0


def get_learning_unit_info(learning_unit_id: str) -> dict:
    """
    Get basic info about a learning unit.
    
    Args:
        learning_unit_id: LearningUnit ID
    
    Returns:
        dict: Learning unit info
    """
    if not learning_unit_id:
        return None
    return frappe.db.get_value(
        "LearningUnit",
        learning_unit_id,
        ["name", "unit_name", "difficulty_tier", "unit_type", "order"],
        as_dict=True
    )


# ============================================================
# CONTENT ITEM QUERIES
# ============================================================

def get_content_items(learning_unit: str) -> list:
    """
    Get all content items for a LearningUnit, ordered by idx.
    
    Args:
        learning_unit: LearningUnit ID
    
    Returns:
        list: List of content items
    """
    return frappe.get_all(
        "UnitContentItem",
        filters={
            "parent": learning_unit,
            "parenttype": "LearningUnit"
        },
        fields=["idx", "content_type", "content", "is_optional"],
        order_by="idx asc"
    )


def get_content_at_index(learning_unit: str, index: int) -> dict:
    """
    Get content item at a specific index.
    
    Args:
        learning_unit: LearningUnit ID
        index: 0-based index position
    
    Returns:
        dict: Content item or None
    """
    content_items = get_content_items(learning_unit)
    
    if index < len(content_items):
        return content_items[index]
    
    return None


def get_total_content_count(learning_unit: str) -> int:
    """
    Get total number of content items in a learning unit.
    """
    return frappe.db.count(
        "UnitContentItem",
        {
            "parent": learning_unit,
            "parenttype": "LearningUnit"
        }
    )


# ============================================================
# CONTENT DETAILS
# ============================================================

def get_content_details(content_type: str, content_id: str, language: str = None) -> dict:
    """
    Get detailed information for a content item.
    """
    if content_type == "VideoClass":
        return get_video_details(content_id, language)
    elif content_type == "Quiz":
        return get_quiz_details(content_id)
    elif content_type == "Assignment":
        return get_assignment_details(content_id)
    elif content_type == "NoteContent":
        return get_note_details(content_id, language)
    elif content_type == "CourseProject":
        return get_project_details(content_id)
    
    return {"name": content_id}


def get_video_details(video_id: str, language: str = None) -> dict:
    """
    Get video details with optional translation.
    """
    try:
        video = frappe.get_doc("VideoClass", video_id)
        
        result = {
            "video_id": video_id,
            "video_name": video.video_name,
            "youtube_url": video.video_youtube_url,
            "plio_url": video.video_plio_url,
            "video_file": video.video_file,
            "duration": str(video.duration) if video.duration else None,
            "description": video.description,
            "difficulty_tier": video.difficulty_tier,
            "translated": False
        }
        
        # Check for translation
        if language and hasattr(video, 'video_translations') and video.video_translations:
            for trans in video.video_translations:
                if trans.language == language:
                    if trans.translated_name:
                        result["video_name"] = trans.translated_name
                    if trans.video_youtube_url:
                        result["youtube_url"] = trans.video_youtube_url
                    if trans.video_plio_url:
                        result["plio_url"] = trans.video_plio_url
                    if hasattr(trans, 'video_file') and trans.video_file:
                        result["video_file"] = trans.video_file
                    result["translated"] = True
                    break
        
        # Set primary URL
        result["url"] = result["youtube_url"] or result["plio_url"] or result["video_file"]
        
        return result
    except Exception as e:
        return {"video_id": video_id, "error": str(e)}


def get_quiz_details(quiz_id: str) -> dict:
    """
    Get quiz details.
    """
    try:
        quiz = frappe.get_doc("Quiz", quiz_id)
        
        # Count questions
        question_count = len(quiz.questions) if hasattr(quiz, 'questions') and quiz.questions else 0
        
        return {
            "quiz_id": quiz_id,
            "quiz_name": quiz.quiz_name if hasattr(quiz, 'quiz_name') else quiz_id,
            "total_questions": question_count,
            "passing_score": flt(quiz.passing_score) if hasattr(quiz, 'passing_score') else 60,
            "time_limit": quiz.time_limit if hasattr(quiz, 'time_limit') else None,
            "difficulty_tier": quiz.difficulty_tier if hasattr(quiz, 'difficulty_tier') else None
        }
    except Exception as e:
        return {"quiz_id": quiz_id, "error": str(e)}


def get_assignment_details(assignment_id: str) -> dict:
    """Get assignment details."""
    try:
        assignment = frappe.get_doc("Assignment", assignment_id)
        return {
            "assignment_id": assignment_id,
            "assignment_name": assignment.assignment_name if hasattr(assignment, 'assignment_name') else assignment_id,
            "description": assignment.description if hasattr(assignment, 'description') else None,
            "due_date": str(assignment.due_date) if hasattr(assignment, 'due_date') and assignment.due_date else None
        }
    except Exception as e:
        return {"assignment_id": assignment_id, "error": str(e)}


def get_note_details(note_id: str, language: str = None) -> dict:
    """Get note content details."""
    try:
        note = frappe.get_doc("NoteContent", note_id)
        return {
            "note_id": note_id,
            "note_name": note.note_name if hasattr(note, 'note_name') else note_id,
            "content": note.content if hasattr(note, 'content') else None,
            "note_type": note.note_type if hasattr(note, 'note_type') else None
        }
    except Exception as e:
        return {"note_id": note_id, "error": str(e)}


def get_project_details(project_id: str) -> dict:
    """Get course project details."""
    try:
        project = frappe.get_doc("CourseProject", project_id)
        return {
            "project_id": project_id,
            "project_name": project.project_name if hasattr(project, 'project_name') else project_id,
            "description": project.description if hasattr(project, 'description') else None
        }
    except Exception as e:
        return {"project_id": project_id, "error": str(e)}


def resolve_student_id(identifier: str) -> str:
    """
    Resolve various identifiers to student ID.
    
    Args:
        identifier: Can be student ID, Glific ID, or phone number
    
    Returns:
        str: Student document ID or None
    """
    if not identifier:
        return None
        
    # Check if it's already a valid student ID
    if frappe.db.exists("Student", identifier):
        return identifier
    
    # Try Glific ID
    student = frappe.db.get_value("Student", {"glific_id": identifier}, "name")
    if student:
        return student
    
    # Try phone number
    student = frappe.db.get_value("Student", {"phone": identifier}, "name")
    if student:
        return student
    
    # Try phone with country code variations
    if identifier.startswith("91") and len(identifier) > 10:
        phone_without_code = identifier[2:]
        student = frappe.db.get_value("Student", {"phone": phone_without_code}, "name")
        if student:
            return student
    
    return None


# ============================================================
# MAIN API: GET NEXT CONTENT
# ============================================================

@frappe.whitelist(allow_guest=False)
def get_next_content(student_id: str, course_level: str, language: str = None):
    """
    Get the next content item for a student.
    
    This is the PRIMARY API for fetching what content a student should consume next.
    
    Args:
        student_id: Student ID (can be Glific ID or phone - will be resolved)
        course_level: Course Level ID
        language: Optional language code for translations
    
    Returns:
        dict: Response with content details or status
    """
    try:
        # Validate inputs
        if not student_id or not course_level:
            return {
                "success": False,
                "error": "student_id and course_level are required"
            }
        
        # Resolve student ID
        resolved_student = resolve_student_id(student_id)
        if not resolved_student:
            return {
                "success": False,
                "error": f"Student not found for identifier: {student_id}"
            }
        
        # Validate course level exists
        if not frappe.db.exists("Course Level", course_level):
            return {
                "success": False,
                "error": f"Course Level '{course_level}' not found"
            }
        
        # STEP 1: Get or create progress record
        progress = get_or_create_student_progress(resolved_student, course_level)
        
        # STEP 2: Get content items for current LU
        content_items = get_content_items(progress["stage"])
        total_content = len(content_items)
        current_index = cint(progress["current_content_index"])
        
        # STEP 3: Check if within bounds (has more content)
        if current_index < total_content:
            # Return current content item
            current_item = content_items[current_index]
            return format_content_response(
                progress=progress,
                content_item=current_item,
                total_content=total_content,
                language=language
            )
        
        # STEP 4: Current LU complete - find next LU in same week/tier
        next_lu = get_next_learning_unit(
            course_level=course_level,
            week_no=progress["current_week"],
            tier=progress["current_tier"],
            after_lu=progress["stage"]
        )
        
        if next_lu:
            # Move to next LU
            update_student_progress(progress["name"], {
                "stage": next_lu,
                "current_content_index": 0,
                "status": "in_progress"
            })
            
            # Get first content of next LU
            content_items = get_content_items(next_lu)
            progress["stage"] = next_lu
            progress["current_content_index"] = 0
            
            if content_items:
                return format_content_response(
                    progress=progress,
                    content_item=content_items[0],
                    total_content=len(content_items),
                    language=language,
                    new_learning_unit=True
                )
        
        # STEP 5: Week/Tier complete - move to next week
        next_week = cint(progress["current_week"]) + 1
        next_tier = get_tier_for_week(next_week)
        
        # Check if next week exists
        if not check_week_exists(course_level, next_week):
            # Course complete!
            update_student_progress(progress["name"], {
                "status": "completed",
                "completion_timestamp": now_datetime()
            })
            
            return {
                "success": True,
                "status": "course_complete",
                "message": "Congratulations! You have completed the course.",
                "student_id": resolved_student,
                "course_level": course_level,
                "completed_week": progress["current_week"],
                "total_weeks_completed": progress["current_week"]
            }
        
        # Find first LU for next week
        first_lu_next_week = get_first_learning_unit(
            course_level=course_level,
            week_no=next_week,
            tier=next_tier
        )
        
        if not first_lu_next_week:
            return {
                "success": False,
                "error": f"No Learning Unit found for Week {next_week} {next_tier} tier"
            }
        
        # Update progress to next week
        update_student_progress(progress["name"], {
            "stage": first_lu_next_week,
            "current_week": next_week,
            "current_tier": next_tier,
            "current_content_index": 0,
            "is_on_remedial": 0,
            "status": "in_progress"
        })
        
        # Return stage complete message with next content preview
        content_items = get_content_items(first_lu_next_week)
        lu_info = get_learning_unit_info(first_lu_next_week)
        
        return {
            "success": True,
            "status": "stage_complete",
            "message": f"Congratulations! You've completed Stage {progress['current_week']}!",
            "student_id": resolved_student,
            "course_level": course_level,
            "completed_week": progress["current_week"],
            "next_week": next_week,
            "next_tier": next_tier,
            "next_learning_unit": first_lu_next_week,
            "next_learning_unit_name": lu_info["unit_name"] if lu_info else None,
            "next_content_preview": {
                "content_type": content_items[0]["content_type"],
                "content_id": content_items[0]["content"]
            } if content_items else None
        }
        
    except Exception as e:
        frappe.log_error(
            f"get_next_content error: {str(e)}\n"
            f"student_id: {student_id}, course_level: {course_level}",
            "Student Progression API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


def format_content_response(
    progress: dict,
    content_item: dict,
    total_content: int,
    language: str = None,
    new_learning_unit: bool = False
) -> dict:
    """
    Format the response for get_next_content.
    """
    # Get learning unit info
    lu_info = get_learning_unit_info(progress["stage"])
    
    # Get content details
    content_details = get_content_details(
        content_type=content_item["content_type"],
        content_id=content_item["content"],
        language=language
    )
    
    current_index = cint(progress["current_content_index"])
    
    return {
        "success": True,
        "status": "content_available",
        
        # Position info
        "student_id": progress.get("student"),
        "current_week": cint(progress["current_week"]),
        "current_tier": progress["current_tier"],
        "is_on_remedial": bool(progress.get("is_on_remedial")),
        
        # Learning Unit info
        "learning_unit": progress["stage"],
        "learning_unit_name": lu_info["unit_name"] if lu_info else None,
        "new_learning_unit": new_learning_unit,
        
        # Content info
        "content_type": content_item["content_type"],
        "content_id": content_item["content"],
        "content_order": current_index + 1,
        "total_content_in_unit": total_content,
        "is_optional": bool(content_item.get("is_optional")),
        
        # Content details
        "content_details": content_details,
        
        # Navigation hints
        "is_first_content": current_index == 0,
        "is_last_content": current_index == total_content - 1,
        "progress_in_unit": {
            "completed": current_index,
            "total": total_content,
            "percentage": round((current_index / total_content) * 100, 1) if total_content > 0 else 0
        }
    }


# ============================================================
# MAIN API: MARK CONTENT COMPLETE
# ============================================================

@frappe.whitelist(allow_guest=False)
def mark_content_complete(
    student_id: str,
    course_level: str,
    content_type: str,
    content_id: str,
    quiz_score: float = None,
    quiz_passed: bool = None
):
    """
    Mark current content as complete and handle progression.
    
    Args:
        student_id: Student ID
        course_level: Course Level ID
        content_type: Type of content (VideoClass, Quiz, etc.)
        content_id: Content document ID
        quiz_score: Score achieved (required for Quiz)
        quiz_passed: Whether quiz was passed (required for Quiz)
    
    Returns:
        dict: Response with action taken
    """
    try:
        # Validate inputs
        if not all([student_id, course_level, content_type, content_id]):
            return {
                "success": False,
                "error": "student_id, course_level, content_type, and content_id are required"
            }
        
        if content_type not in VALID_CONTENT_TYPES:
            return {
                "success": False,
                "error": f"Invalid content_type. Must be one of: {VALID_CONTENT_TYPES}"
            }
        
        # Resolve student ID
        resolved_student = resolve_student_id(student_id)
        if not resolved_student:
            return {
                "success": False,
                "error": f"Student not found for identifier: {student_id}"
            }
        
        # Get progress record
        progress = get_or_create_student_progress(resolved_student, course_level)
        
        # Validate content matches current position
        current_content = get_content_at_index(
            progress["stage"],
            cint(progress["current_content_index"])
        )
        
        if not current_content:
            return {
                "success": False,
                "error": "No content found at current position"
            }
        
        if current_content["content"] != content_id:
            return {
                "success": False,
                "error": f"Content mismatch. Expected '{current_content['content']}', "
                         f"got '{content_id}'. Must complete content in order.",
                "expected_content": current_content["content"],
                "received_content": content_id
            }
        
        # Validate content type matches
        if current_content["content_type"] != content_type:
            return {
                "success": False,
                "error": f"Content type mismatch. Expected '{current_content['content_type']}', "
                         f"got '{content_type}'."
            }
        
        # Handle Quiz
        if content_type == "Quiz":
            if quiz_passed is None:
                return {
                    "success": False,
                    "error": "quiz_passed is required for Quiz content"
                }
            
            # Convert to boolean
            quiz_passed = quiz_passed in [True, "true", "True", 1, "1"]
            quiz_score = flt(quiz_score) if quiz_score is not None else 0
            
            if not quiz_passed:
                return handle_quiz_failure(progress, course_level, quiz_score)
            else:
                return handle_quiz_success(progress, course_level, quiz_score)
        
        # Non-quiz content: normal progression
        return advance_to_next_content(progress, course_level)
        
    except Exception as e:
        frappe.log_error(
            f"mark_content_complete error: {str(e)}\n"
            f"student_id: {student_id}, content_id: {content_id}",
            "Student Progression API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


def handle_quiz_failure(progress: dict, course_level: str, quiz_score: float) -> dict:
    """
    Handle quiz failure - switch to Remedial or restart Remedial.
    """
    is_on_remedial = bool(progress.get("is_on_remedial"))
    current_week = cint(progress["current_week"])
    
    if is_on_remedial:
        # Already on Remedial path
        content_items = get_content_items(progress["stage"])
        current_index = cint(progress["current_content_index"])
        
        if current_index < len(content_items) - 1:
            # More content after this quiz - continue to next content
            new_index = current_index + 1
            update_student_progress(progress["name"], {
                "current_content_index": new_index
            })
            
            next_content = content_items[new_index]
            
            return {
                "success": True,
                "action": "continue_remedial",
                "message": "Keep practicing! Continue with the next content.",
                "quiz_result": {
                    "score": quiz_score,
                    "passed": False
                },
                "current_week": current_week,
                "current_tier": "Remedial",
                "next_content": {
                    "content_type": next_content["content_type"],
                    "content_id": next_content["content"],
                    "content_order": new_index + 1
                }
            }
        else:
            # No more content - RESTART Remedial from beginning
            remedial_attempts = cint(progress.get("remedial_attempts", 0)) + 1
            
            update_student_progress(progress["name"], {
                "current_content_index": 0,
                "remedial_attempts": remedial_attempts
            })
            
            first_content = content_items[0] if content_items else None
            
            return {
                "success": True,
                "action": "restart_remedial",
                "message": "Let's review the material again from the beginning.",
                "quiz_result": {
                    "score": quiz_score,
                    "passed": False
                },
                "current_week": current_week,
                "current_tier": "Remedial",
                "remedial_attempt": remedial_attempts,
                "next_content": {
                    "content_type": first_content["content_type"],
                    "content_id": first_content["content"],
                    "content_order": 1
                } if first_content else None
            }
    
    else:
        # First time failing primary quiz - switch to Remedial
        remedial_lu = get_first_learning_unit(
            course_level=course_level,
            week_no=current_week,
            tier=REMEDIAL_TIER
        )
        
        if not remedial_lu:
            return {
                "success": False,
                "error": f"No Remedial content configured for Week {current_week}. "
                         "Please contact support."
            }
        
        update_student_progress(progress["name"], {
            "stage": remedial_lu,
            "current_tier": REMEDIAL_TIER,
            "current_content_index": 0,
            "is_on_remedial": 1,
            "remedial_attempts": 1
        })
        
        content_items = get_content_items(remedial_lu)
        first_content = content_items[0] if content_items else None
        lu_info = get_learning_unit_info(remedial_lu)
        
        return {
            "success": True,
            "action": "switched_to_remedial",
            "message": "Don't worry! Let's review with some additional content to help you learn better.",
            "quiz_result": {
                "score": quiz_score,
                "passed": False
            },
            "current_week": current_week,
            "previous_tier": progress["current_tier"],
            "new_tier": REMEDIAL_TIER,
            "new_learning_unit": remedial_lu,
            "new_learning_unit_name": lu_info["unit_name"] if lu_info else None,
            "next_content": {
                "content_type": first_content["content_type"],
                "content_id": first_content["content"],
                "content_order": 1
            } if first_content else None
        }


def handle_quiz_success(progress: dict, course_level: str, quiz_score: float) -> dict:
    """
    Handle quiz success - potentially exit Remedial path.
    """
    is_on_remedial = bool(progress.get("is_on_remedial"))
    
    if is_on_remedial:
        return exit_remedial_path(progress, course_level, quiz_score)
    else:
        return advance_to_next_content(progress, course_level, quiz_score=quiz_score)


def exit_remedial_path(progress: dict, course_level: str, quiz_score: float) -> dict:
    """
    Exit Remedial path after passing a Remedial quiz.
    """
    current_week = cint(progress["current_week"])
    next_week = current_week + 1
    next_tier = get_tier_for_week(next_week)
    
    # Check if next week exists
    if not check_week_exists(course_level, next_week):
        # Course complete!
        update_student_progress(progress["name"], {
            "status": "completed",
            "is_on_remedial": 0,
            "completion_timestamp": now_datetime()
        })
        
        return {
            "success": True,
            "action": "course_complete",
            "message": "Congratulations! You have completed the course!",
            "quiz_result": {
                "score": quiz_score,
                "passed": True
            },
            "completed_week": current_week,
            "exited_remedial": True
        }
    
    # Find first LU for next week
    first_lu_next_week = get_first_learning_unit(
        course_level=course_level,
        week_no=next_week,
        tier=next_tier
    )
    
    if not first_lu_next_week:
        return {
            "success": False,
            "error": f"No Learning Unit found for Week {next_week} {next_tier} tier"
        }
    
    update_student_progress(progress["name"], {
        "stage": first_lu_next_week,
        "current_week": next_week,
        "current_tier": next_tier,
        "current_content_index": 0,
        "is_on_remedial": 0
    })
    
    content_items = get_content_items(first_lu_next_week)
    first_content = content_items[0] if content_items else None
    lu_info = get_learning_unit_info(first_lu_next_week)
    
    return {
        "success": True,
        "action": "exit_remedial_to_next_week",
        "message": f"Great job! You've mastered the material. Moving to Stage {next_week}!",
        "quiz_result": {
            "score": quiz_score,
            "passed": True
        },
        "completed_week": current_week,
        "exited_remedial": True,
        "new_week": next_week,
        "new_tier": next_tier,
        "new_learning_unit": first_lu_next_week,
        "new_learning_unit_name": lu_info["unit_name"] if lu_info else None,
        "next_content": {
            "content_type": first_content["content_type"],
            "content_id": first_content["content"],
            "content_order": 1
        } if first_content else None
    }


def advance_to_next_content(progress: dict, course_level: str, quiz_score: float = None) -> dict:
    """
    Move to next content item (normal progression).
    """
    current_index = cint(progress["current_content_index"])
    new_index = current_index + 1
    content_items = get_content_items(progress["stage"])
    
    if new_index < len(content_items):
        # More content in current LU
        update_student_progress(progress["name"], {
            "current_content_index": new_index,
            "status": "in_progress"
        })
        
        next_content = content_items[new_index]
        
        result = {
            "success": True,
            "action": "next_content",
            "message": "Content completed! Continue with the next item.",
            "current_week": cint(progress["current_week"]),
            "current_tier": progress["current_tier"],
            "progress_in_unit": {
                "completed": new_index,
                "total": len(content_items),
                "percentage": round((new_index / len(content_items)) * 100, 1)
            },
            "next_content": {
                "content_type": next_content["content_type"],
                "content_id": next_content["content"],
                "content_order": new_index + 1
            }
        }
        
        if quiz_score is not None:
            result["quiz_result"] = {"score": quiz_score, "passed": True}
        
        return result
    
    # Current LU complete - find next LU in same week/tier
    next_lu = get_next_learning_unit(
        course_level=course_level,
        week_no=progress["current_week"],
        tier=progress["current_tier"],
        after_lu=progress["stage"]
    )
    
    if next_lu:
        update_student_progress(progress["name"], {
            "stage": next_lu,
            "current_content_index": 0
        })
        
        content_items = get_content_items(next_lu)
        first_content = content_items[0] if content_items else None
        lu_info = get_learning_unit_info(next_lu)
        
        result = {
            "success": True,
            "action": "next_learning_unit",
            "message": "Learning Unit completed! Moving to the next one.",
            "current_week": cint(progress["current_week"]),
            "current_tier": progress["current_tier"],
            "completed_learning_unit": progress["stage"],
            "new_learning_unit": next_lu,
            "new_learning_unit_name": lu_info["unit_name"] if lu_info else None,
            "next_content": {
                "content_type": first_content["content_type"],
                "content_id": first_content["content"],
                "content_order": 1
            } if first_content else None
        }
        
        if quiz_score is not None:
            result["quiz_result"] = {"score": quiz_score, "passed": True}
        
        return result
    
    # Week complete - move to next week
    current_week = cint(progress["current_week"])
    next_week = current_week + 1
    next_tier = get_tier_for_week(next_week)
    
    if not check_week_exists(course_level, next_week):
        # Course complete!
        update_student_progress(progress["name"], {
            "status": "completed",
            "completion_timestamp": now_datetime()
        })
        
        result = {
            "success": True,
            "action": "course_complete",
            "message": "Congratulations! You have completed the course!",
            "completed_week": current_week
        }
        
        if quiz_score is not None:
            result["quiz_result"] = {"score": quiz_score, "passed": True}
        
        return result
    
    # Find first LU for next week
    first_lu_next_week = get_first_learning_unit(
        course_level=course_level,
        week_no=next_week,
        tier=next_tier
    )
    
    if not first_lu_next_week:
        return {
            "success": False,
            "error": f"No Learning Unit found for Week {next_week} {next_tier} tier"
        }
    
    update_student_progress(progress["name"], {
        "stage": first_lu_next_week,
        "current_week": next_week,
        "current_tier": next_tier,
        "current_content_index": 0,
        "is_on_remedial": 0
    })
    
    content_items = get_content_items(first_lu_next_week)
    first_content = content_items[0] if content_items else None
    lu_info = get_learning_unit_info(first_lu_next_week)
    
    result = {
        "success": True,
        "action": "week_complete",
        "message": f"Congratulations! You've completed Stage {current_week}! Moving to Stage {next_week}.",
        "completed_week": current_week,
        "new_week": next_week,
        "new_tier": next_tier,
        "new_learning_unit": first_lu_next_week,
        "new_learning_unit_name": lu_info["unit_name"] if lu_info else None,
        "next_content": {
            "content_type": first_content["content_type"],
            "content_id": first_content["content"],
            "content_order": 1
        } if first_content else None
    }
    
    if quiz_score is not None:
        result["quiz_result"] = {"score": quiz_score, "passed": True}
    
    return result


# ============================================================
# MAIN API: GET STUDENT PROGRESS
# ============================================================

@frappe.whitelist(allow_guest=False)
def get_student_progress(student_id: str, course_level: str):
    """
    Get comprehensive progress information for a student.
    """
    try:
        # Validate inputs
        if not student_id or not course_level:
            return {
                "success": False,
                "error": "student_id and course_level are required"
            }
        
        # Resolve student ID
        resolved_student = resolve_student_id(student_id)
        if not resolved_student:
            return {
                "success": False,
                "error": f"Student not found for identifier: {student_id}"
            }
        
        # Get student info
        student = frappe.db.get_value(
            "Student",
            resolved_student,
            ["name", "name1", "phone", "glific_id"],
            as_dict=True
        )
        
        # Get course info
        course = frappe.db.get_value(
            "Course Level",
            course_level,
            ["name", "name1"],
            as_dict=True
        )
        
        if not course:
            return {
                "success": False,
                "error": f"Course Level '{course_level}' not found"
            }
        
        # Get or create progress
        progress = get_or_create_student_progress(resolved_student, course_level)
        
        # Get current LU info
        lu_info = get_learning_unit_info(progress["stage"])
        
        # Get content items for current LU
        content_items = get_content_items(progress["stage"])
        current_index = cint(progress["current_content_index"])
        
        # Get total weeks in course
        total_weeks_result = frappe.db.sql("""
            SELECT MAX(week_no) as max_week
            FROM `tabLearningUnitList`
            WHERE parent = %s AND parenttype = 'Course Level'
        """, course_level, as_dict=True)
        total_weeks = total_weeks_result[0].max_week if total_weeks_result and total_weeks_result[0].max_week else 1
        
        # Get current content
        current_content = None
        if current_index < len(content_items):
            item = content_items[current_index]
            current_content = {
                "content_type": item["content_type"],
                "content_id": item["content"],
                "content_order": current_index + 1
            }
        
        return {
            "success": True,
            
            "student": {
                "id": student["name"],
                "name": student.get("name1"),
                "phone": student.get("phone"),
                "glific_id": student.get("glific_id")
            },
            
            "course": {
                "id": course["name"],
                "name": course.get("name1"),
                "total_stages": cint(total_weeks)
            },
            
            "current_position": {
                "stage": cint(progress["current_week"]),
                "tier": progress["current_tier"],
                "learning_unit": progress["stage"],
                "learning_unit_name": lu_info["unit_name"] if lu_info else None,
                "content_index": current_index,
                "is_on_remedial": bool(progress.get("is_on_remedial")),
                "remedial_attempts": cint(progress.get("remedial_attempts", 0))
            },
            
            "current_content": current_content,
            
            "stage_progress": {
                "content_completed": current_index,
                "content_total": len(content_items),
                "percentage": round((current_index / len(content_items)) * 100, 1) if content_items else 0
            },
            
            "overall_progress": {
                "stages_completed": cint(progress["current_week"]) - 1,
                "stages_total": cint(total_weeks),
                "percentage": round(((cint(progress["current_week"]) - 1) / cint(total_weeks)) * 100, 1) if total_weeks else 0
            },
            
            "status": progress.get("status", "assigned"),
            "started_at": str(progress.get("start_timestamp")) if progress.get("start_timestamp") else None,
            "last_activity_at": str(progress.get("last_activity_timestamp")) if progress.get("last_activity_timestamp") else None
        }
        
    except Exception as e:
        frappe.log_error(
            f"get_student_progress error: {str(e)}\n"
            f"student_id: {student_id}, course_level: {course_level}",
            "Student Progression API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }

# ============================================================
# API: GET QUIZ BY ID
# ============================================================
# Add this function to tap_lms/journey/student_progression.py
#
# Same response format as get_student_quiz_content but with simpler inputs:
# - student_id: Student identifier
# - quiz_id: Quiz document ID
# - language (optional): Falls back to student's language

@frappe.whitelist(allow_guest=False)
def get_quiz_by_id():
    """
    Get quiz content by quiz_id for a student.
    Same response format as get_student_quiz_content.
    
    Request Body (JSON):
        {
            "student_id": "ST00001388",
            "quiz_id": "BasicQuiz_Quiz_B-basic",
            "language": "English"  // optional
        }
    
    Returns:
        dict: Quiz information with questions in flat format
    """
    try:
        # Get data from request body
        data = frappe.request.get_json() if frappe.request.data else {}
        
        student_id = data.get("student_id")
        quiz_id = data.get("quiz_id")
        language = data.get("language")
        
        # Validate inputs
        if not student_id or not quiz_id:
            return {
                "success": False,
                "error": "student_id and quiz_id are required"
            }
        
        # Resolve student ID
        resolved_student = resolve_student_id(student_id)
        if not resolved_student:
            return {
                "success": False,
                "error": f"Student not found for identifier: {student_id}"
            }
        
        # Get student's language if not provided
        if not language:
            student_lang = frappe.db.get_value("Student", resolved_student, "language")
            language = student_lang if student_lang else "English"
        
        # Check if quiz exists
        if not frappe.db.exists("Quiz", quiz_id):
            return {
                "success": False,
                "error": f"Quiz '{quiz_id}' not found"
            }
        
        # Get quiz with questions
        quiz_info = _get_quiz_with_questions_flat(quiz_id, language)
        
        if not quiz_info:
            return {
                "success": False,
                "error": f"No questions found for quiz '{quiz_id}'"
            }
        
        # Build flat response structure (same as get_student_quiz_content)
        response = {
            "success": True,
            "quiz_count": 1
        }
        
        # Add quiz as quiz_1 with questions as question_1, question_2, etc.
        quiz_data = {
            "quiz_id": quiz_info["quiz_id"],
            "quiz_name": quiz_info["quiz_name"],
            "total_questions": quiz_info["total_questions"]
        }
        
        # Add questions as individual fields
        for question in quiz_info["questions"]:
            question_key = f"question_{question['order']}"
            quiz_data[question_key] = question["question_text"]
        
        quiz_data["language"] = quiz_info["language"]
        response["quiz_1"] = quiz_data
        
        return response
        
    except Exception as e:
        frappe.log_error(
            f"get_quiz_by_id error: {str(e)}\n"
            f"student_id: {student_id}, quiz_id: {quiz_id}",
            "Student Progression API Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


def _get_quiz_with_questions_flat(quiz_id: str, language: str) -> dict:
    """
    Get quiz information with questions and translations.
    Helper function for get_quiz_by_id.
    
    Args:
        quiz_id: Quiz ID
        language: Language for translation
        
    Returns:
        dict: Quiz information with questions list
    """
    try:
        # Get Quiz document
        quiz_doc = frappe.get_doc("Quiz", quiz_id)
        
        quiz_name = quiz_doc.quiz_name
        
        # Get questions from quiz
        questions_list = []
        
        if hasattr(quiz_doc, 'questions') and quiz_doc.questions:
            for question_row in quiz_doc.questions:
                question_id = question_row.question
                question_number = question_row.question_number if hasattr(question_row, 'question_number') else question_row.idx
                
                if not question_id:
                    continue
                
                # Get question details and check for translation
                question_text = _get_question_text_translated(question_id, language)
                
                if question_text:
                    questions_list.append({
                        "order": question_number,
                        "question_id": question_id,
                        "question_text": question_text
                    })
        
        # Skip if no questions
        if not questions_list:
            return None
        
        # Sort by order
        questions_list.sort(key=lambda x: x["order"])
        
        return {
            "quiz_id": quiz_id,
            "quiz_name": quiz_name,
            "total_questions": len(questions_list),
            "questions": questions_list,
            "language": language
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error getting quiz with questions: {str(e)}",
            "Student Progression API"
        )
        return None


def _get_question_text_translated(question_id: str, language: str) -> str:
    """
    Get question text with translation if available.
    
    Args:
        question_id: QuizQuestion ID
        language: Language for translation
        
    Returns:
        str: Question text (translated if available)
    """
    try:
        # Get QuizQuestion document
        question_doc = frappe.get_doc("QuizQuestion", question_id)
        
        question_text = question_doc.question
        
        # Try to find translation for the specified language
        if language and hasattr(question_doc, 'question_translations') and question_doc.question_translations:
            for translation in question_doc.question_translations:
                if translation.language == language and translation.translated_question:
                    question_text = translation.translated_question
                    break
        
        return question_text
        
    except Exception as e:
        frappe.log_error(
            f"Error getting question text: {str(e)}",
            "Student Progression API"
        )
        return None
