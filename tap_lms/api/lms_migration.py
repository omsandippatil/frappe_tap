import frappe
import re
import json


VERTICAL_MAPPING = {
    "STEM-Coding":     {"name1": "STEM - Coding",      "name2": "Coding"},
    "STEM-Science":    {"name1": "STEM - Science",     "name2": "Science Lab"},
    "Visual-Arts":     {"name1": "Visual Arts",        "name2": "Arts"},
    "VA":              {"name1": "Visual Arts",        "name2": "Arts"},
    "Performing-Arts": {"name1": "Performing Arts",    "name2": "Dance"},
    "Dance":           {"name1": "Performing Arts",    "name2": "Dance"},
    "Fin-Lit":         {"name1": "Financial Literacy", "name2": "Financial Literacy"},
}

COURSE_MAPPING = {
    "STEM-Coding":     {"name1": "Coding",             "name2": "STEM - Coding"},
    "STEM-Science":    {"name1": "Science",            "name2": "STEM - Science"},
    "Visual-Arts":     {"name1": "Arts",               "name2": "Visual Arts"},
    "VA":              {"name1": "Arts",               "name2": "Visual Arts"},
    "Performing-Arts": {"name1": "Dance",              "name2": "Performing Arts"},
    "Dance":           {"name1": "Dance",              "name2": "Performing Arts"},
    "Fin-Lit":         {"name1": "Financial Literacy", "name2": "Financial Literacy"},
}

CORRECT_OPTION_MAP = {
    "A": 1, "B": 2, "C": 3,
    "OPTION A": 1, "OPTION B": 2, "OPTION C": 3,
    "OPTIONA": 1, "OPTIONB": 2, "OPTIONC": 3,
    "OPT A": 1, "OPT B": 2, "OPT C": 3,
    "OPTA": 1, "OPTB": 2, "OPTC": 3,
    "1": 1, "2": 2, "3": 3,
    "OPTION 1": 1, "OPTION 2": 2, "OPTION 3": 3,
    "OPT 1": 1, "OPT 2": 2, "OPT 3": 3,
}

LANGUAGE_CONFIG = {
    "Hinglish": ("Hinglish", "hi"),
    "Hindi":    ("Hindi",    "hi"),
    "Marathi":  ("Marathi",  "mr"),
    "Punjabi":  ("Punjabi",  "pa"),
}

ACTIVITY_TYPE_MAP = {
    "engagement": "engagement",
    "regular":    "regular",
    "baseline":   "baseline",
    "challenge":  "challenge",
    "hol":        "hol",
}

VALID_ACTIVITY_TYPES = {"engagement", "regular", "baseline", "challenge", "hol"}

MASTERY_LEVEL_MAP = {
    "Basic":        "Basic",
    "Intermediate": "Proficient",
    "Proficient":   "Proficient",
    "Advanced":     "Advanced",
    "Remedial":     "Basic",
}

SDG_LABEL_MAP = {
    1:  "No Poverty",
    2:  "Zero Hunger",
    3:  "Good Health and Well-being",
    4:  "Quality Education",
    5:  "Gender Equality",
    6:  "Clean Water and Sanitation",
    7:  "Affordable and Clean Energy",
    8:  "Decent Work and Economic Growth",
    9:  "Industry, Innovation and Infrastructure",
    10: "Reduced Inequalities",
    11: "Sustainable Cities and Communities",
    12: "Responsible Consumption and Production",
    13: "Climate Action",
    14: "Life Below Water",
    15: "Life on Land",
    16: "Peace, Justice and Strong Institutions",
    17: "Partnerships for the Goals",
}


def clean(val):
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s.upper() in ("N/A", "NA", "-", "NONE", "NULL", "") else s


def vertical_name2(key):
    return VERTICAL_MAPPING.get(key, {}).get("name2", key)


def slugify(val):
    s = str(val).strip()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s)
    return s.strip("-")


def parse_correct_option(raw):
    if not raw:
        return 1
    r = re.sub(r"\s+", " ", str(raw).strip().upper())
    if r in CORRECT_OPTION_MAP:
        return CORRECT_OPTION_MAP[r]
    rns = r.replace(" ", "")
    if rns in CORRECT_OPTION_MAP:
        return CORRECT_OPTION_MAP[rns]
    for letter, num in [("A", 1), ("B", 2), ("C", 3)]:
        if r.endswith(letter):
            return num
    for digit, num in [("1", 1), ("2", 2), ("3", 3)]:
        if r.endswith(digit):
            return num
    return 1


def norm_activity_type(raw):
    if not raw:
        return None
    key = str(raw).strip().lower()
    mapped = ACTIVITY_TYPE_MAP.get(key)
    return mapped if mapped else None


def norm_mastery_level(difficulty_tier):
    return MASTERY_LEVEL_MAP.get(str(difficulty_tier).strip(), "Basic")


def parse_sdg_list(raw):
    if not raw:
        return []
    numbers = re.findall(r"\d+", str(raw))
    result = []
    for n in numbers:
        num = int(n)
        if 1 <= num <= 17:
            result.append(num)
    return list(dict.fromkeys(result))


def make_unique_doc_name(doctype, base_name, max_len=140):
    base_name = base_name[:max_len]
    if not frappe.db.exists(doctype, base_name):
        return base_name
    counter = 1
    while True:
        suffix = "-{}".format(counter)
        candidate = base_name[: max_len - len(suffix)] + suffix
        if not frappe.db.exists(doctype, candidate):
            return candidate
        counter += 1


def make_unique_field_value(doctype, field, base_value, max_len=140):
    base_value = base_value[:max_len]
    if not frappe.db.get_value(doctype, {field: base_value}, "name"):
        return base_value
    counter = 1
    while True:
        suffix = "-{}".format(counter)
        candidate = base_value[: max_len - len(suffix)] + suffix
        if not frappe.db.get_value(doctype, {field: candidate}, "name"):
            return candidate
        counter += 1


def ensure_language(lang_name):
    if not lang_name:
        return None
    info = LANGUAGE_CONFIG.get(lang_name)
    if not info:
        return None
    doc_name = info[0]
    if not frappe.db.exists("TAP Language", doc_name):
        try:
            frappe.get_doc({
                "doctype":       "TAP Language",
                "language_name": doc_name,
                "language_code": info[1],
            }).insert(ignore_permissions=True)
            frappe.db.commit()
        except Exception:
            pass
    return doc_name


def ensure_sdg_goal(sdg_number):
    doc_name = "SDG-{}".format(sdg_number)
    if frappe.db.exists("SDG Goal", doc_name):
        return doc_name
    goal_name = SDG_LABEL_MAP.get(sdg_number, "SDG {}".format(sdg_number))
    try:
        doc = frappe.get_doc({
            "doctype":    "SDG Goal",
            "name":       doc_name,
            "sdg_number": sdg_number,
            "goal_name":  goal_name,
        })
        doc.flags.name_set = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc_name
    except Exception:
        frappe.db.rollback()
        if frappe.db.exists("SDG Goal", doc_name):
            return doc_name
        raise


def get_or_create_vertical(key, is_hol=False):
    mapping = VERTICAL_MAPPING.get(key)
    if not mapping:
        return None
    name1 = mapping["name1"]
    name2 = mapping["name2"]

    if is_hol:
        name1 = "{} HOL".format(name1)
        name2 = "{} HOL".format(name2)

    existing = (
        frappe.db.get_value("Course Verticals", {"name2": name2}, "name")
        or frappe.db.get_value("Course Verticals", {"name1": name1}, "name")
    )
    if existing:
        return existing

    vertical_id = re.sub(r"[^A-Za-z0-9]", "_", name2).upper()
    try:
        doc = frappe.get_doc({
            "doctype":     "Course Verticals",
            "name1":       name1,
            "name2":       name2,
            "vertical_id": vertical_id,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Vertical Insert Error")
        frappe.db.rollback()
        existing = (
            frappe.db.get_value("Course Verticals", {"name2": name2}, "name")
            or frappe.db.get_value("Course Verticals", {"name1": name1}, "name")
        )
        if existing:
            return existing
        raise


def get_or_create_course(vertical_key, is_hol=False):
    mapping = COURSE_MAPPING.get(vertical_key)
    if not mapping:
        return None
    name1 = mapping["name1"]
    name2 = mapping["name2"]

    if is_hol:
        name1 = "{} HOL".format(name1)
        name2 = "{} HOL".format(name2)

    existing = (
        frappe.db.get_value("Course", {"name2": name2}, "name")
        or frappe.db.get_value("Course", {"name1": name1}, "name")
    )
    if existing:
        return existing

    try:
        doc = frappe.get_doc({
            "doctype": "Course",
            "name1":   name1,
            "name2":   name2,
        })
        doc.name = name2
        doc.flags.name_set = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Course Insert Error")
        frappe.db.rollback()
        existing = (
            frappe.db.get_value("Course", {"name2": name2}, "name")
            or frappe.db.get_value("Course", {"name1": name1}, "name")
        )
        if existing:
            return existing
        raise


def get_or_create_course_level(vertical_key, course, curriculum_type, level="1"):
    is_hol = str(curriculum_type).strip().upper() == "HOL"
    vertical_doc_name = get_or_create_vertical(vertical_key, is_hol=is_hol)
    if not vertical_doc_name:
        raise ValueError("Cannot resolve vertical for key: {}".format(vertical_key))

    curr = "HOL" if is_hol else "Main"
    level_str = str(level).strip() or "1"
    name1 = "{}-{}-Level-{}".format(slugify(course), curr, level_str)

    existing = frappe.db.get_value("Course Level", {"name1": name1, "vertical": vertical_doc_name}, "name")
    if existing:
        return existing, name1

    existing2 = frappe.db.get_value("Course Level", {"name1": name1}, "name")
    if existing2:
        return existing2, name1

    vs_slug = slugify(vertical_name2(vertical_key))
    if is_hol:
        vs_slug = "{}-HOL".format(vs_slug)
    base_doc_id = "{}-{}-{}-Level-{}".format(slugify(course), vs_slug, curr, level_str)
    doc_id = make_unique_doc_name("Course Level", base_doc_id)

    existing3 = frappe.db.get_value("Course Level", doc_id, "name")
    if existing3:
        return existing3, name1

    try:
        doc = frappe.get_doc({
            "doctype":  "Course Level",
            "name":     doc_id,
            "name1":    name1,
            "vertical": vertical_doc_name,
        })
        doc.flags.name_set = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name, name1
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Course Level Error")
        frappe.db.rollback()
        found = (
            frappe.db.get_value("Course Level", {"name1": name1}, "name")
            or frappe.db.get_value("Course Level", doc_id, "name")
        )
        if found:
            return found, name1
        raise


def get_or_create_competency(name_val):
    cleaned = clean(name_val)
    if not cleaned:
        return None
    existing = frappe.db.get_value("Competency", {"comp_name": cleaned}, "name")
    if existing:
        return existing
    try:
        doc = frappe.get_doc({
            "doctype":   "Competency",
            "comp_name": cleaned,
            "category":  "Creative",
        })
        doc.name = cleaned
        doc.flags.name_set = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Competency Error")
        frappe.db.rollback()
        existing = frappe.db.get_value("Competency", {"comp_name": cleaned}, "name")
        if existing:
            return existing
        raise


def get_or_create_learning_objective(activity_name, objective_text, outcomes_text, difficulty_tier, vertical_key, is_hol):
    if not activity_name:
        return None
    vertical_doc_name = get_or_create_vertical(vertical_key, is_hol=is_hol)
    if not vertical_doc_name:
        return None

    existing = frappe.db.get_value(
        "Learning Objective",
        {"objective_name": activity_name, "difficulty_tier": difficulty_tier, "subject": vertical_doc_name},
        "name",
    )
    if existing:
        return existing

    vs_slug = slugify(vertical_name2(vertical_key))
    if is_hol:
        vs_slug = "{}-HOL".format(vs_slug)
    base_doc_name = "{}-{}-{}-LO".format(vs_slug, difficulty_tier, slugify(activity_name))
    doc_name = make_unique_doc_name("Learning Objective", base_doc_name)

    desc = clean(outcomes_text) or clean(objective_text) or ""

    try:
        doc = frappe.get_doc({
            "doctype":         "Learning Objective",
            "name":            doc_name,
            "objective_name":  activity_name[:140],
            "description":     desc[:500] if desc else None,
            "subject":         vertical_doc_name,
            "difficulty_tier": difficulty_tier or "Basic",
        })
        doc.flags.name_set = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Learning Objective Error")
        frappe.db.rollback()
        existing = frappe.db.get_value(
            "Learning Objective",
            {"objective_name": activity_name, "difficulty_tier": difficulty_tier, "subject": vertical_doc_name},
            "name",
        )
        if existing:
            return existing
        raise


def get_next_unit_order(course_level_name):
    try:
        cl_doc = frappe.get_doc("Course Level", course_level_name)
        return len(cl_doc.learning_units or []) + 1
    except Exception:
        return 1


def get_or_create_learning_unit(
    vertical_key, course_level_name, curriculum_type,
    row_slug, activity_name, unit_type, difficulty_tier,
    unit_meta, status, competency_name, learning_obj_name, activity_type, is_hol,
):
    base_unit_doc_name = slugify(row_slug)[:140] if row_slug else "{}-{}-{}".format(
        slugify(activity_name), difficulty_tier, course_level_name
    )[:140]
    unit_doc_name = make_unique_doc_name("LearningUnit", base_unit_doc_name)

    if frappe.db.exists("LearningUnit", unit_doc_name) and unit_doc_name == base_unit_doc_name:
        return unit_doc_name

    vertical_doc_name = get_or_create_vertical(vertical_key, is_hol=is_hol)
    row_order          = get_next_unit_order(course_level_name)

    description    = clean((unit_meta or {}).get("content_knowledge", ""))
    have_you_heard = clean((unit_meta or {}).get("have_you_heard_of", ""))
    outcomes       = clean((unit_meta or {}).get("outcomes", ""))
    real_world     = have_you_heard or outcomes
    estimated_dur  = clean((unit_meta or {}).get("estimated_duration", ""))
    normalized_at  = norm_activity_type(activity_type)
    mastery_level  = norm_mastery_level(difficulty_tier)

    competencies = []
    if competency_name:
        competencies.append({"competency": competency_name})

    objectives = []
    if learning_obj_name:
        objectives.append({
            "learning_objectives":  learning_obj_name,
            "importance_level":     "Primary",
            "target_mastery_level": mastery_level,
        })

    sdg_rows = []
    sdg_raw = clean((unit_meta or {}).get("sdg", ""))
    if sdg_raw:
        for sdg_num in parse_sdg_list(sdg_raw):
            try:
                sdg_doc_name = ensure_sdg_goal(sdg_num)
                sdg_rows.append({"sdg_goal": sdg_doc_name})
            except Exception:
                frappe.log_error(frappe.get_traceback(), "SDG Goal Error {}".format(sdg_num))

    try:
        doc = frappe.get_doc({
            "doctype":                "LearningUnit",
            "name":                   unit_doc_name,
            "unit_name":              (activity_name or "Unit {}".format(row_order))[:140],
            "unit_type":              unit_type or "Module",
            "course_vertical":        vertical_doc_name,
            "difficulty_tier":        difficulty_tier or "Basic",
            "order":                  row_order,
            "status":                 status or "Published",
            "activity_type":          normalized_at,
            "description":            description[:500] if description else None,
            "real_world_connection":  real_world[:500] if real_world else None,
            "estimated_duration":     estimated_dur or None,
            "competencies_addressed": competencies,
            "learning_objectives":    objectives,
            "sdg_alignment":          sdg_rows,
            "content_items":          [],
        })
        doc.flags.name_set = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "LearningUnit Error")
        frappe.db.rollback()
        if frappe.db.exists("LearningUnit", unit_doc_name):
            return unit_doc_name
        raise


def link_unit_to_course_level(course_level_name, learning_unit_name, week_no, row_order):
    try:
        cl_doc = frappe.get_doc("Course Level", course_level_name)
        if any(r.learning_unit == learning_unit_name for r in (cl_doc.learning_units or [])):
            return
        try:
            week = int(float(str(week_no).strip())) if clean(str(week_no)) else None
        except (ValueError, TypeError):
            week = None
        if not week:
            week = row_order or (len(cl_doc.learning_units or []) + 1)
        cl_doc.append("learning_units", {
            "learning_unit": learning_unit_name,
            "week_no":       week,
        })
        cl_doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(str(e), "Unit-CourseLevel Link Error")


def create_quiz_option(option_text, option_number, translations_data):
    trans_rows = []
    for lang_name, trans_text in translations_data:
        t = clean(trans_text)
        if t:
            lang = ensure_language(lang_name)
            if lang:
                trans_rows.append({
                    "language":          lang,
                    "translated_option": t,
                })
    try:
        doc = frappe.get_doc({
            "doctype":             "QuizOption",
            "option_text":         (clean(option_text) or "Option {}".format(chr(64 + option_number)))[:500],
            "option_number":       option_number,
            "option_translations": trans_rows,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "QuizOption Error")
        raise


def create_quiz_question(q_data, activity_name, q_index, prefix="AQ"):
    q_name = "{} {}{}QN{:04d}".format(activity_name, prefix, q_index, q_index)
    q_name = make_unique_doc_name("QuizQuestion", q_name)
    if frappe.db.exists("QuizQuestion", q_name):
        return q_name

    correct_int = parse_correct_option(q_data.get("correct_option", "A") or "A")

    option_rows = []
    for opt_num, opt_key in [(1, "option_a"), (2, "option_b"), (3, "option_c")]:
        opt_text = clean(q_data.get(opt_key, "")) or "Option {}".format(chr(64 + opt_num))
        trans = []
        for lang in ["Hindi", "Marathi", "Punjabi"]:
            lb = q_data.get(lang.lower()) or {}
            t = clean(lb.get(opt_key, ""))
            if t:
                trans.append((lang, t))
        opt_name = create_quiz_option(opt_text, opt_num, trans)
        if opt_name:
            option_rows.append({"options": opt_name, "order_number": opt_num})

    q_trans_rows = []
    for lang in ["Hindi", "Marathi", "Punjabi"]:
        lb = q_data.get(lang.lower()) or {}
        tq = clean(lb.get("question", ""))
        if tq:
            ld = ensure_language(lang)
            if ld:
                q_trans_rows.append({"language": ld, "translated_question": tq})

    q_type_raw = clean(q_data.get("question_type", "")) or "Multiple Choice"
    if q_type_raw.upper() in ("MCQ", "MULTIPLE CHOICE", "MC", "MULTIPLE_CHOICE"):
        question_type = "Multiple Choice"
    else:
        question_type = q_type_raw

    hint_val = clean(q_data.get("hint", ""))
    try:
        points_int = int(float(str(q_data.get("points", 3)))) if clean(str(q_data.get("points", 3))) else 3
    except (ValueError, TypeError):
        points_int = 3

    try:
        doc = frappe.get_doc({
            "doctype":               "QuizQuestion",
            "name":                  q_name,
            "question_name":         q_name,
            "question":              clean(q_data.get("question", "")),
            "question_type":         question_type,
            "options":               option_rows,
            "points":                points_int,
            "correct_option":        correct_int,
            "hint":                  hint_val or None,
            "question_translations": q_trans_rows,
        })
        doc.flags.name_set = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "QuizQuestion Error")
        frappe.db.rollback()
        if frappe.db.exists("QuizQuestion", q_name):
            return q_name
        raise


def create_quiz(quiz_doc_name, quiz_display_name, questions_data, activity_name, difficulty_tier, status, prefix):
    quiz_doc_name = make_unique_doc_name("Quiz", quiz_doc_name)

    existing_by_name = frappe.db.get_value("Quiz", {"quiz_name": quiz_display_name[:140]}, "name")
    if existing_by_name:
        return existing_by_name

    unique_display_name = make_unique_field_value("Quiz", "quiz_name", quiz_display_name[:140])

    q_rows = []
    for i, q in enumerate(questions_data, 1):
        if not clean(q.get("question", "")):
            continue
        qn = create_quiz_question(q, activity_name, i, prefix=prefix)
        if qn:
            q_rows.append({"question_number": i, "question": qn})

    if not q_rows:
        return None

    try:
        doc = frappe.get_doc({
            "doctype":            "Quiz",
            "name":               quiz_doc_name,
            "quiz_name":          unique_display_name,
            "difficulty_tier":    difficulty_tier or "Basic",
            "total_questions":    len(q_rows),
            "passing_score":      12,
            "time_limit":         "00:10:00",
            "estimated_duration": "00:02:00",
            "max_attempts":       "3",
            "status":             status or "Published",
            "questions":          q_rows,
        })
        doc.flags.name_set = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Quiz Error")
        frappe.db.rollback()
        if frappe.db.exists("Quiz", quiz_doc_name):
            return quiz_doc_name
        raise


def create_video_class(activity_name, video_data, difficulty_tier, vertical_key, status, is_hol, row_slug):
    vs_slug = slugify(vertical_name2(vertical_key))
    if is_hol:
        vs_slug = "{}-HOL".format(vs_slug)

    base_video_doc_name = (
        slugify("{}-video".format(row_slug))[:140]
        if row_slug
        else "{}-{}-{}-{}".format(
            slugify(video_data.get("_course") or vertical_name2(vertical_key)),
            vs_slug, difficulty_tier, slugify(activity_name)
        )[:140]
    )
    video_doc_name = make_unique_doc_name("VideoClass", base_video_doc_name)

    if frappe.db.exists("VideoClass", video_doc_name) and video_doc_name == base_video_doc_name:
        return video_doc_name

    vertical_doc_name   = get_or_create_vertical(vertical_key, is_hol=is_hol)
    yt_hinglish         = clean(video_data.get("youtube_hinglish",    ""))
    drive_hinglish      = clean(video_data.get("drive_hinglish",      ""))
    plio_hinglish       = clean(video_data.get("plio_hinglish",       ""))
    transcript_hinglish = clean(video_data.get("transcript_hinglish", ""))

    trans_rows = []
    for lang_display, lang_key in [
        ("Hindi",   "hindi"),
        ("Marathi", "marathi"),
        ("Punjabi", "punjabi"),
    ]:
        yt_url    = clean(video_data.get("youtube_{}".format(lang_key),    ""))
        drive_url = clean(video_data.get("drive_{}".format(lang_key),      ""))
        plio_url  = clean(video_data.get("plio_{}".format(lang_key),       ""))
        t_script  = clean(video_data.get("transcript_{}".format(lang_key), ""))
        t_desc    = clean(video_data.get("description_{}".format(lang_key),""))

        if not any([yt_url, drive_url, plio_url, t_script, t_desc]):
            continue

        lang_doc = ensure_language(lang_display)
        if not lang_doc:
            continue

        trans_rows.append({
            "language":               lang_doc,
            "translated_name":        activity_name[:140],
            "translated_description": t_desc[:140] if t_desc else None,
            "video_youtube_url":      yt_url or None,
            "video_file":             drive_url or None,
            "video_plio_url":         plio_url or None,
            "video_transcript":       t_script[:140] if t_script else None,
        })

    raw_valid    = clean(video_data.get("valid_invalid", "")).upper()
    video_status = "Draft" if raw_valid == "INVALID" else (status or "Published")

    _desc_raw              = clean(video_data.get("description_english", ""))
    desc_val               = _desc_raw[:500] if _desc_raw else None
    estimated_duration_val = clean(video_data.get("estimated_duration", "")) or None
    teacher_note_val       = clean(video_data.get("activity_note", ""))

    assessment_rows = []
    activity_quiz_name = video_data.get("_activity_quiz_name")
    if activity_quiz_name:
        assessment_rows.append({"assessment_type": "Quiz", "assessment": activity_quiz_name})

    try:
        doc = frappe.get_doc({
            "doctype":            "VideoClass",
            "name":               video_doc_name,
            "video_name":         activity_name[:140],
            "course_vertical":    vertical_doc_name,
            "difficulty_tier":    difficulty_tier or "Basic",
            "description":        desc_val,
            "duration":           "00:00:00",
            "video_youtube_url":  yt_hinglish or None,
            "video_file":         drive_hinglish or None,
            "video_plio_url":     plio_hinglish or None,
            "video_transcript":   transcript_hinglish[:500] if transcript_hinglish else None,
            "estimated_duration": estimated_duration_val,
            "status":             video_status,
            "video_translations": trans_rows,
            "assessments":        assessment_rows,
        })
        doc.flags.name_set = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "VideoClass Error")
        frappe.db.rollback()
        if frappe.db.exists("VideoClass", video_doc_name):
            return video_doc_name
        raise


def link_quiz_to_video(video_name, quiz_name):
    try:
        video_doc = frappe.get_doc("VideoClass", video_name)
        if any(r.assessment == quiz_name for r in (video_doc.assessments or [])):
            return
        video_doc.append("assessments", {"assessment_type": "Quiz", "assessment": quiz_name})
        video_doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(str(e), "Quiz-VideoClass Link Error")


def link_content_to_unit(learning_unit_name, content_items, teacher_note):
    try:
        lu_doc = frappe.get_doc("LearningUnit", learning_unit_name)
        existing_keys = {(r.content_type, r.content) for r in (lu_doc.content_items or [])}
        changed = False
        truncated_note = (teacher_note or "")[:140]
        for i, item in enumerate(content_items):
            key = (item["content_type"], item["content"])
            if key not in existing_keys:
                lu_doc.append("content_items", {
                    "content_type":     item["content_type"],
                    "content":          item["content"],
                    "is_optional":      0,
                    "order":            i + 1,
                    "note_for_teacher": truncated_note if item["content_type"] == "VideoClass" else "",
                })
                existing_keys.add(key)
                changed = True
        if changed:
            lu_doc.save(ignore_permissions=True)
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(str(e), "Content-Unit Link Error")


@frappe.whitelist(allow_guest=False)
def migrate_activity(data):
    try:
        data = frappe.parse_json(data)

        vertical_key    = data.get("vertical", "")
        curriculum_type = data.get("curriculum_type", "Main") or "Main"
        is_hol          = str(curriculum_type).strip().upper() == "HOL"
        course          = data.get("course", "")
        activity_name   = data.get("activity_name", "Unnamed Activity")
        difficulty_tier = data.get("difficulty_tier", "Basic") or "Basic"
        unit_meta       = data.get("unit_meta") or {}
        row_order       = int(data.get("order", 0) or 0)
        row_slug        = data.get("row_slug", "") or ""
        unit_type       = data.get("unit_type", "Module") or "Module"
        status          = data.get("status", "Published") or "Published"
        activity_type   = data.get("activity_type", "") or ""
        week_no         = data.get("week", "") or ""

        created = {}

        if vertical_key not in VERTICAL_MAPPING:
            return {
                "success":         False,
                "message":         "Unrecognised vertical key: {}".format(vertical_key),
                "created_records": {},
            }

        vertical_name = get_or_create_vertical(vertical_key, is_hol=is_hol)
        if not vertical_name:
            return {
                "success":         False,
                "message":         "Failed to create Course Verticals for: {}".format(vertical_key),
                "created_records": {},
            }
        created["vertical"] = vertical_name

        course_doc_name = get_or_create_course(vertical_key, is_hol=is_hol)
        if course_doc_name:
            created["course"] = course_doc_name

        level = str(data.get("level", "1") or "1").strip()
        course_level_result = get_or_create_course_level(vertical_key, course, curriculum_type, level=level)
        if not course_level_result or not course_level_result[0]:
            return {"success": False, "message": "Failed to create Course Level", "created_records": created}
        course_level_name, course_level_label = course_level_result
        created["course_level"] = course_level_name

        competency_name = get_or_create_competency(unit_meta.get("skills_21st_century", ""))
        if competency_name:
            created["competency"] = competency_name

        objective_name = get_or_create_learning_objective(
            activity_name,
            clean(unit_meta.get("objective", "")),
            clean(unit_meta.get("outcomes", "")),
            difficulty_tier,
            vertical_key,
            is_hol,
        )
        if objective_name:
            created["learning_objective"] = objective_name

        activity_quiz_questions = data.get("activity_quiz") or []
        activity_quiz_name = None
        if activity_quiz_questions:
            vs_slug     = slugify(vertical_name2(vertical_key))
            co_slug     = slugify(course)
            if is_hol:
                vs_slug = "{}-HOL".format(vs_slug)
            aq_doc_name = "{}-{}-{}-{}-AQ".format(co_slug, vs_slug, difficulty_tier, slugify(activity_name))[:140]
            activity_quiz_name = create_quiz(
                aq_doc_name,
                "{} Activity Quiz".format(activity_name),
                activity_quiz_questions,
                activity_name,
                difficulty_tier,
                status,
                "AQ",
            )
            if activity_quiz_name:
                created["activity_quiz"] = activity_quiz_name

        video_data   = data.get("video_data") or {}
        teacher_note = clean(video_data.get("activity_note", ""))

        video_data["_course"]            = course
        video_data["_vertical"]          = vertical_key
        video_data["estimated_duration"] = (
            clean(unit_meta.get("estimated_duration", ""))
            or clean(video_data.get("estimated_duration", ""))
        )
        if activity_quiz_name:
            video_data["_activity_quiz_name"] = activity_quiz_name

        video_name = None
        if video_data and any(
            clean(video_data.get(k, ""))
            for k in [
                "youtube_hinglish", "youtube_hindi", "youtube_marathi", "youtube_punjabi",
                "plio_hinglish", "plio_hindi", "plio_marathi", "plio_punjabi",
                "drive_hinglish", "drive_hindi", "drive_marathi", "drive_punjabi",
                "description_english", "transcript_english",
            ]
        ):
            video_name = create_video_class(
                activity_name, video_data, difficulty_tier, vertical_key, status, is_hol, row_slug
            )
            if video_name:
                created["video"] = video_name

        if video_name and activity_quiz_name:
            existing_video = frappe.get_doc("VideoClass", video_name)
            if not any(r.assessment == activity_quiz_name for r in (existing_video.assessments or [])):
                link_quiz_to_video(video_name, activity_quiz_name)

        learning_unit_name = get_or_create_learning_unit(
            vertical_key, course_level_name, curriculum_type,
            row_slug, activity_name, unit_type, difficulty_tier,
            unit_meta, status, competency_name, objective_name, activity_type, is_hol,
        )
        if not learning_unit_name:
            return {"success": False, "message": "Failed to create LearningUnit", "created_records": created}
        created["learning_unit"] = learning_unit_name

        link_unit_to_course_level(course_level_name, learning_unit_name, week_no, row_order)

        content_items = []
        if video_name:
            content_items.append({"content_type": "VideoClass", "content": video_name})
        if activity_quiz_name:
            content_items.append({"content_type": "Quiz", "content": activity_quiz_name})

        if content_items:
            link_content_to_unit(learning_unit_name, content_items, teacher_note)

        frappe.db.commit()
        return {
            "success":         True,
            "message":         "Activity migrated successfully",
            "created_records": created,
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "LMS Migration Error")
        frappe.db.rollback()
        return {"success": False, "message": str(e), "created_records": {}}
