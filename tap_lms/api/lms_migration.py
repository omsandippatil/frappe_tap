import frappe
from frappe import _
import re


VERTICAL_MAPPING = {
    "STEM-Coding":     {"name1": "STEM - Coding",      "name2": "Coding",             "vertical_id": "STEM-Coding"},
    "STEM-Science":    {"name1": "STEM - Science",     "name2": "Science Lab",         "vertical_id": "STEM-Science"},
    "Visual-Arts":     {"name1": "Visual Arts",        "name2": "Arts",                "vertical_id": "Visual-Arts"},
    "VA":              {"name1": "Visual Arts",        "name2": "Arts",                "vertical_id": "Visual-Arts"},
    "Performing-Arts": {"name1": "Performing Arts",    "name2": "Dance",               "vertical_id": "Performing-Arts"},
    "Dance":           {"name1": "Performing Arts",    "name2": "Dance",               "vertical_id": "Performing-Arts"},
    "Fin-Lit":         {"name1": "Financial Literacy", "name2": "Financial Literacy",  "vertical_id": "Fin-Lit"},
}

CORRECT_OPTION_MAP = {
    "A": 1, "B": 2, "C": 3, "D": 4,
    "OPTION A": 1, "OPTION B": 2, "OPTION C": 3, "OPTION D": 4,
    "OPT A": 1, "OPT B": 2, "OPT C": 3, "OPT D": 4,
    "1": 1, "2": 2, "3": 3, "4": 4,
    "OPTION 1": 1, "OPTION 2": 2, "OPTION 3": 3, "OPTION 4": 4,
    "OPT 1": 1, "OPT 2": 2, "OPT 3": 3, "OPT 4": 4,
    "OPTIONA": 1, "OPTIONB": 2, "OPTIONC": 3, "OPTIOND": 4,
    "OPTION1": 1, "OPTION2": 2, "OPTION3": 3, "OPTION4": 4,
    "OPTA": 1, "OPTB": 2, "OPTC": 3, "OPTD": 4,
    "OPT1": 1, "OPT2": 2, "OPT3": 3, "OPT4": 4,
}


@frappe.whitelist(allow_guest=False)
def migrate_activity(data):
    try:
        data = frappe.parse_json(data)

        result = {
            "success": False,
            "message": "",
            "created_records": {}
        }

        vertical_raw    = data.get("vertical", "")
        curriculum_type = data.get("curriculum_type", "Main") or "Main"
        course_raw      = data.get("course", "")
        activity_name   = data.get("activity_name", "Unnamed Activity")
        difficulty_tier = data.get("difficulty_tier", "Basic") or "Basic"
        unit_meta       = data.get("unit_meta", {}) or {}
        order_val       = int(data.get("order", 0) or 0)
        unit_raw        = data.get("unit", "1") or "1"
        unit_type       = data.get("unit_type", "Module") or "Module"
        doc_status      = data.get("status", "Published") or "Published"

        vertical_doc_name = get_or_create_vertical(vertical_raw)
        if not vertical_doc_name:
            result["message"] = f"Failed to create vertical: {vertical_raw}"
            return result
        result["created_records"]["vertical"] = vertical_doc_name

        course_level_name = get_or_create_course_level(vertical_raw, course_raw, curriculum_type)
        if not course_level_name:
            result["message"] = "Failed to create course level"
            return result
        result["created_records"]["course_level"] = course_level_name

        competency_name = None
        skills_raw = clean_val(unit_meta.get("skills_21st_century", ""))
        if skills_raw:
            competency_name = get_or_create_competency(skills_raw)

        learning_obj_name = None
        objective_raw = clean_val(unit_meta.get("objective", ""))
        if objective_raw:
            learning_obj_name = get_or_create_learning_objective(
                activity_name,
                objective_raw,
                difficulty_tier,
                vertical_raw
            )

        learning_unit_name = get_or_create_learning_unit(
            unit_raw,
            unit_type,
            course_level_name,
            curriculum_type,
            difficulty_tier,
            order_val,
            unit_meta,
            doc_status,
            competency_name,
            learning_obj_name,
            vertical_raw
        )
        if not learning_unit_name:
            result["message"] = "Failed to create learning unit"
            return result
        result["created_records"]["learning_unit"] = learning_unit_name

        link_unit_to_course_level(course_level_name, learning_unit_name, order_val)

        content_items = []
        video_data    = data.get("video_data") or {}
        activity_note = clean_val(video_data.get("activity_note", ""))

        video_name = None
        if video_data:
            video_name = create_video_class(
                activity_name,
                video_data,
                difficulty_tier,
                vertical_raw,
                doc_status
            )
            if video_name:
                content_items.append({
                    "content_type":     "VideoClass",
                    "content":          video_name,
                    "is_optional":      0,
                    "order_no":         1,
                    "note_for_teacher": activity_note
                })
                result["created_records"]["video"] = video_name

        activity_quiz_data = data.get("activity_quiz")
        if activity_quiz_data:
            activity_quiz_name = create_activity_quiz(
                activity_name,
                activity_quiz_data,
                difficulty_tier,
                doc_status
            )
            if activity_quiz_name:
                content_items.append({
                    "content_type": "Quiz",
                    "content":      activity_quiz_name,
                    "is_optional":  0,
                    "order_no":     2
                })
                result["created_records"]["activity_quiz"] = activity_quiz_name
                if video_name:
                    link_quiz_to_video(video_name, activity_quiz_name)

        plio_quiz_data = data.get("plio_quiz")
        if plio_quiz_data:
            plio_quiz_name = create_plio_quiz(
                activity_name,
                plio_quiz_data,
                difficulty_tier,
                doc_status
            )
            if plio_quiz_name:
                content_items.append({
                    "content_type": "Quiz",
                    "content":      plio_quiz_name,
                    "is_optional":  0,
                    "order_no":     3
                })
                result["created_records"]["plio_quiz"] = plio_quiz_name
                if video_name:
                    link_quiz_to_video(video_name, plio_quiz_name)

        if content_items:
            link_content_to_unit(learning_unit_name, content_items)

        result["success"] = True
        result["message"] = "Activity migrated successfully"
        frappe.db.commit()
        return result

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "LMS Migration Error")
        return {
            "success": False,
            "message": str(e),
            "created_records": {}
        }


def clean_val(val):
    if not val:
        return ""
    s = str(val).strip()
    return "" if s in ("N/A", "-", "NA", "None", "none", "NONE") else s


def get_vertical_short(vertical_name):
    return VERTICAL_MAPPING.get(vertical_name, {}).get("name2", vertical_name)


def parse_correct_option(raw_value):
    if not raw_value:
        return 1
    raw = str(raw_value).strip().upper()
    raw = re.sub(r'\s+', ' ', raw)
    if raw in CORRECT_OPTION_MAP:
        return CORRECT_OPTION_MAP[raw]
    raw_no_space = raw.replace(" ", "")
    if raw_no_space in CORRECT_OPTION_MAP:
        return CORRECT_OPTION_MAP[raw_no_space]
    for letter, num in [("A", 1), ("B", 2), ("C", 3), ("D", 4)]:
        if raw.endswith(letter):
            return num
    for digit, num in [("1", 1), ("2", 2), ("3", 3), ("4", 4)]:
        if raw.endswith(digit):
            return num
    return 1


def ensure_language(lang_name):
    if not lang_name:
        return None
    lang_map = {
        "English":  ("English",  "en"),
        "Hindi":    ("Hindi",    "hi"),
        "Marathi":  ("Marathi",  "mr"),
        "Punjabi":  ("Punjabi",  "pa"),
        "Hinglish": ("Hinglish", "hi"),
    }
    mapped   = lang_map.get(lang_name, (lang_name, lang_name[:2].lower()))
    doc_name = mapped[0]
    if not frappe.db.exists("TAP Language", doc_name):
        try:
            doc = frappe.get_doc({
                "doctype":       "TAP Language",
                "language_name": doc_name,
                "language_code": mapped[1]
            })
            doc.insert(ignore_permissions=True)
        except Exception:
            pass
    return doc_name


def get_or_create_vertical(vertical_name):
    mapping = VERTICAL_MAPPING.get(vertical_name)
    if not mapping:
        return None

    name2 = mapping["name2"]
    if frappe.db.exists("Course Verticals", name2):
        return name2

    try:
        doc = frappe.get_doc({
            "doctype":     "Course Verticals",
            "name1":       mapping["name1"],
            "name2":       name2,
            "vertical_id": mapping["vertical_id"]
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception as e:
        frappe.log_error(str(e), "Vertical Creation Error")
        return None


def get_or_create_course_level(vertical, course, curriculum_type):
    vertical_short = get_vertical_short(vertical)
    is_hol         = str(curriculum_type).upper() == "HOL"
    course_label   = f"{course} HOL" if is_hol else f"{course} Main"

    existing = frappe.db.get_value(
        "Course Level",
        {"name1": course_label, "vertical": vertical_short},
        "name"
    )
    if existing:
        return existing

    existing_any = frappe.db.get_all(
        "Course Level",
        filters={"name1": course_label},
        pluck="name",
        limit=1
    )
    if existing_any:
        return existing_any[0]

    try:
        doc = frappe.get_doc({
            "doctype":  "Course Level",
            "name1":    course_label,
            "vertical": vertical_short,
            "status":   "Published",
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception as e:
        frappe.log_error(str(e), "Course Level Creation Error")
        return None


def get_or_create_competency(competency_name):
    cleaned = clean_val(competency_name)
    if not cleaned:
        return None

    existing = frappe.db.get_value("Competency", {"comp_name": cleaned}, "name")
    if existing:
        return existing

    try:
        doc = frappe.get_doc({
            "doctype":   "Competency",
            "comp_name": cleaned,
            "category":  "Creative"
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception as e:
        frappe.log_error(str(e), "Competency Creation Error")
        return None


def get_or_create_learning_objective(activity_name, objective_text, difficulty_tier, vertical_name):
    if not objective_text:
        return None

    vertical_short = get_vertical_short(vertical_name)

    existing = frappe.db.get_value(
        "Learning Objective",
        {"objective_name": activity_name, "difficulty_tier": difficulty_tier, "subject": vertical_short},
        "name"
    )
    if existing:
        return existing

    existing_count = frappe.db.count("Learning Objective", filters={"subject": vertical_short})
    counter        = (existing_count or 0) + 1
    doc_name       = f"{activity_name}-{difficulty_tier}-{vertical_short}-{counter:04d}"

    try:
        doc = frappe.get_doc({
            "doctype":         "Learning Objective",
            "name":            doc_name,
            "objective_name":  activity_name,
            "description":     objective_text,
            "subject":         vertical_short,
            "difficulty_tier": difficulty_tier or "Basic"
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception as e:
        frappe.log_error(str(e), "Learning Objective Creation Error")
        return None


def get_or_create_learning_unit(unit_raw, unit_type, course_level_name, curriculum_type, difficulty_tier, order, unit_meta, status, competency_name, learning_obj_name, vertical_name):
    is_hol        = str(curriculum_type).upper() == "HOL"
    curr_prefix   = "HOL" if is_hol else "Main"
    unit_doc_name = f"{curr_prefix}-{unit_type}-{course_level_name}-{difficulty_tier}-{order}"

    if frappe.db.exists("LearningUnit", unit_doc_name):
        return unit_doc_name

    vertical_short  = get_vertical_short(vertical_name)
    description_val = clean_val((unit_meta or {}).get("content_knowledge", ""))
    real_world_val  = clean_val((unit_meta or {}).get("material_required", ""))

    competencies_list = []
    if competency_name:
        competencies_list.append({"competency": competency_name})

    unit_learning_objectives = []
    if learning_obj_name:
        unit_learning_objectives.append({
            "learning_objectives":  learning_obj_name,
            "importance_level":     "Primary",
            "target_mastery_level": difficulty_tier or "Basic"
        })

    try:
        doc = frappe.get_doc({
            "doctype":                  "LearningUnit",
            "name":                     unit_doc_name,
            "unit_name":                unit_raw or "1",
            "unit_type":                unit_type or "Module",
            "course_vertical":          vertical_short,
            "difficulty_tier":          difficulty_tier or "Basic",
            "order":                    order or 0,
            "status":                   status or "Published",
            "estimated_duration":       "0",
            "description":              description_val or None,
            "real_world_connection":    real_world_val or None,
            "competencies_addressed":   competencies_list,
            "unit_learning_objectives": unit_learning_objectives,
            "content_items":            []
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception as e:
        frappe.log_error(str(e), "Learning Unit Creation Error")
        return None


def link_unit_to_course_level(course_level_name, learning_unit_name, order_val):
    try:
        course_doc     = frappe.get_doc("Course Level", course_level_name)
        already_linked = any(
            row.learning_unit == learning_unit_name
            for row in (course_doc.learning_units or [])
        )
        if not already_linked:
            week_no = len(course_doc.learning_units or []) + 1
            course_doc.append("learning_units", {
                "learning_unit": learning_unit_name,
                "week_no":       week_no,
                "order_no":      order_val or week_no
            })
            course_doc.save(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(str(e), "Unit-CourseLevel Link Error")


def link_quiz_to_video(video_name, quiz_name):
    try:
        video_doc      = frappe.get_doc("VideoClass", video_name)
        already_linked = any(
            row.assessment == quiz_name
            for row in (video_doc.assessments or [])
        )
        if not already_linked:
            video_doc.append("assessments", {
                "assessment_type": "Quiz",
                "assessment":      quiz_name
            })
            video_doc.save(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(str(e), "Quiz-VideoClass Link Error")


def build_option_row(question_data, opt_key, opt_num):
    opt_text = clean_val(question_data.get(opt_key, ""))
    if not opt_text:
        opt_text = f"Option {chr(64 + opt_num)}"

    option_translations = []
    for lang in ["Hindi", "Marathi", "Punjabi"]:
        lang_block = question_data.get(lang.lower(), {}) or {}
        trans_text = clean_val(lang_block.get(opt_key, ""))
        if trans_text:
            lang_name = ensure_language(lang)
            if lang_name:
                option_translations.append({
                    "language":          lang_name,
                    "translated_option": trans_text
                })

    return {
        "option_text":         opt_text,
        "option_number":       opt_num,
        "option_translations": option_translations
    }


def build_question_translations(question_data):
    translations = []
    for lang in ["Hindi", "Marathi", "Punjabi"]:
        lang_block = question_data.get(lang.lower(), {}) or {}
        trans_q    = clean_val(lang_block.get("question", ""))
        if trans_q:
            lang_name = ensure_language(lang)
            if lang_name:
                translations.append({
                    "language":            lang_name,
                    "translated_question": trans_q,
                })
    return translations


def create_quiz_question_doc(question_data, activity_name, question_number, quiz_type_prefix):
    question_name = f"{activity_name} {quiz_type_prefix}{question_number}QN{question_number:04d}"

    if frappe.db.exists("QuizQuestion", question_name):
        return question_name

    correct_raw = question_data.get("correct_option", "A") or "A"
    correct_int = parse_correct_option(correct_raw)

    hint_val = clean_val(question_data.get("hint", ""))

    options = [
        build_option_row(question_data, "option_a", 1),
        build_option_row(question_data, "option_b", 2),
        build_option_row(question_data, "option_c", 3),
    ]

    question_translations = build_question_translations(question_data)

    try:
        doc = frappe.get_doc({
            "doctype":               "QuizQuestion",
            "name":                  question_name,
            "question_name":         question_name,
            "question":              question_data.get("question", "") or "",
            "question_type":         question_data.get("question_type", "Multiple Choice") or "Multiple Choice",
            "options":               options,
            "points":                int(question_data.get("points", 3) or 3),
            "correct_option":        correct_int,
            "hint":                  hint_val or None,
            "question_translations": question_translations
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception as e:
        frappe.log_error(str(e), "Quiz Question Creation Error")
        return None


def create_activity_quiz(activity_name, questions, difficulty_tier, status):
    quiz_doc_name = f"{activity_name} Activity Quiz-{difficulty_tier}"

    if frappe.db.exists("Quiz", quiz_doc_name):
        return quiz_doc_name

    quiz_questions = []
    for i, q in enumerate(questions, 1):
        q_name = create_quiz_question_doc(q, activity_name, i, "AQ")
        if q_name:
            quiz_questions.append({"question_number": i, "question": q_name})

    try:
        doc = frappe.get_doc({
            "doctype":         "Quiz",
            "quiz_name":       f"{activity_name} Activity Quiz",
            "difficulty_tier": difficulty_tier or "Basic",
            "total_questions": len(quiz_questions),
            "passing_score":   60,
            "max_attempts":    "3",
            "status":          status or "Published",
            "questions":       quiz_questions
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception as e:
        frappe.log_error(str(e), "Activity Quiz Creation Error")
        return None


def create_plio_quiz(activity_name, questions, difficulty_tier, status):
    quiz_doc_name = f"{activity_name} Plio Quiz-{difficulty_tier}"

    if frappe.db.exists("Quiz", quiz_doc_name):
        return quiz_doc_name

    quiz_questions = []
    for i, q in enumerate(questions, 1):
        q_name = create_quiz_question_doc(q, activity_name, i, "PQ")
        if q_name:
            quiz_questions.append({"question_number": i, "question": q_name})

    try:
        doc = frappe.get_doc({
            "doctype":         "Quiz",
            "quiz_name":       f"{activity_name} Plio Quiz",
            "difficulty_tier": difficulty_tier or "Basic",
            "total_questions": len(quiz_questions),
            "passing_score":   60,
            "max_attempts":    "3",
            "status":          status or "Published",
            "questions":       quiz_questions
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception as e:
        frappe.log_error(str(e), "Plio Quiz Creation Error")
        return None


def create_video_class(activity_name, video_data, difficulty_tier, vertical_name, status):
    video_doc_name = f"{activity_name}-{difficulty_tier}"
    vertical_short = get_vertical_short(vertical_name)

    if frappe.db.exists("VideoClass", video_doc_name):
        return video_doc_name

    lang_map = [
        ("Hinglish", "hinglish"),
        ("Hindi",    "hindi"),
        ("Marathi",  "marathi"),
        ("Punjabi",  "punjabi"),
    ]

    translations = []
    for lang_display, lang_key in lang_map:
        youtube_url = clean_val(video_data.get(f"youtube_{lang_key}", ""))
        plio_url    = clean_val(video_data.get(f"plio_{lang_key}", ""))
        drive_url   = clean_val(video_data.get(f"drive_{lang_key}", ""))
        transcript  = clean_val(video_data.get(f"transcript_{lang_key}", ""))
        trans_desc  = clean_val(video_data.get(f"description_{lang_key}", ""))

        if not any([youtube_url, plio_url, drive_url, transcript, trans_desc]):
            continue

        lang_name = ensure_language(lang_display)
        if not lang_name:
            continue

        row = {
            "language":          lang_name,
            "translated_name":   activity_name,
            "video_youtube_url": youtube_url or None,
            "video_plio_url":    plio_url or None,
            "video_file":        drive_url or None,
            "video_transcript":  transcript or None,
        }

        if lang_display != "Hinglish" and trans_desc:
            row["translated_description"] = trans_desc

        translations.append(row)

    description_val    = clean_val(video_data.get("description_english", ""))
    english_transcript = clean_val(video_data.get("transcript_english", ""))
    duration_val       = clean_val(video_data.get("duration", ""))
    estimated_dur_val  = clean_val(video_data.get("estimated_duration", ""))
    video_status       = clean_val(video_data.get("video_status", "")) or status or "Published"

    try:
        doc = frappe.get_doc({
            "doctype":            "VideoClass",
            "video_name":         activity_name,
            "course_vertical":    vertical_short,
            "difficulty_tier":    difficulty_tier or "Basic",
            "description":        description_val or None,
            "video_transcript":   english_transcript or None,
            "duration":           duration_val or None,
            "estimated_duration": estimated_dur_val or None,
            "status":             video_status,
            "video_translations": translations
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception as e:
        frappe.log_error(str(e), "Video Class Creation Error")
        return None


def link_content_to_unit(learning_unit_name, content_items):
    try:
        doc           = frappe.get_doc("LearningUnit", learning_unit_name)
        existing_keys = {
            (row.content_type, row.content)
            for row in (doc.content_items or [])
        }
        for item in content_items:
            key = (item["content_type"], item["content"])
            if key not in existing_keys:
                doc.append("content_items", {
                    "content_type":     item["content_type"],
                    "content":          item["content"],
                    "is_optional":      item.get("is_optional", 0),
                    "order_no":         item.get("order_no", 1),
                    "note_for_teacher": item.get("note_for_teacher", "") or ""
                })
        doc.save(ignore_permissions=True)
        return True
    except Exception as e:
        frappe.log_error(str(e), "Content Linking Error")
        return False