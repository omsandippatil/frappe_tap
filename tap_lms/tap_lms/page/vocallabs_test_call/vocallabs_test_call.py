# -*- coding: utf-8 -*-
import json
import re
import requests
import frappe
from frappe.utils import now_datetime

from tap_lms.summer_program.vocallabs import (
    _get_voice_agent_settings,
    _get_auth_token,
    _resolve_agent_id,
    _http_post,
    _extract_prospect_id,
    _is_duplicate_prospect_response,
    _lookup_prospect_id_by_phone,
    _refresh_contact_data_best_effort,
    _post_initiate_call,
    _safe_summary,
    PermanentVocallabsError,
)


@frappe.whitelist()
def get_initial_data():
    """Return settings, available scripts, and language mappings for the test UI."""
    settings = _get_voice_agent_settings()
    
    settings_data = {
        "enabled": getattr(settings, "enabled", 0) if settings else 0,
        "service_url": getattr(settings, "service_url", "") if settings else "",
        "client_id": getattr(settings, "client_id", "") if settings else "",
        "default_contact_group_id": getattr(settings, "default_contact_group_id", "") if settings else "",
        "fallback_agent_id": getattr(settings, "agent_id", "") if settings else "",
        "default_parent_call_config": getattr(settings, "default_parent_call_config", "") if settings else "",
        "agents": []
    }
    
    if settings and getattr(settings, "agents", None):
        for ag in settings.agents:
            settings_data["agents"].append({
                "language": ag.language,
                "agent_id": ag.agent_id
            })

    # Fetch all ParentCallConfigs
    scripts = frappe.get_all(
        "ParentCallConfig",
        fields=["name", "title", "status_template", "is_active"],
        order_by="name asc"
    )

    # Format script list and language breakdown
    formatted_scripts = []
    lang_counts = {"Hindi": 0, "English": 0, "Marathi": 0, "Punjabi": 0, "Other": 0}
    for s in scripts:
        title_str = (s.get("title") or s.name).lower()
        if "hindi" in title_str:
            lang_counts["Hindi"] += 1
        elif "english" in title_str:
            lang_counts["English"] += 1
        elif "marathi" in title_str:
            lang_counts["Marathi"] += 1
        elif "punjabi" in title_str:
            lang_counts["Punjabi"] += 1
        else:
            lang_counts["Other"] += 1

        formatted_scripts.append({
            "name": s.name,
            "title": s.get("title") or s.name,
            "status_text": s.get("status_template") or "",
            "is_active": s.get("is_active", 1)
        })

    # Stats
    total_calls = 0
    recent_logs = []
    try:
        total_calls = frappe.db.count("ProgramEventLog")
        raw_logs = frappe.get_all(
            "ProgramEventLog",
            fields=["name", "event_type", "student", "batch", "created_at", "details"],
            order_by="created_at desc",
            limit=15
        )
        for rl in raw_logs:
            details_obj = {}
            if rl.get("details"):
                try:
                    details_obj = json.loads(rl.details) if isinstance(rl.details, str) else rl.details
                except Exception:
                    details_obj = {"raw": rl.details}
            recent_logs.append({
                "name": rl.name,
                "event_type": rl.event_type,
                "student": rl.student,
                "batch": rl.batch,
                "created_at": str(rl.created_at) if rl.created_at else "",
                "details": details_obj
            })
    except Exception:
        pass

    students_count = 0
    try:
        students_count = frappe.db.count("Student")
    except Exception:
        pass

    return {
        "settings": settings_data,
        "scripts": formatted_scripts,
        "stats": {
            "total_scripts": len(formatted_scripts),
            "total_calls": total_calls,
            "students_count": students_count,
            "lang_counts": lang_counts
        },
        "recent_logs": recent_logs
    }


@frappe.whitelist()
def get_script_detail(script_name):
    """Return specific script fields for dynamic variable parsing."""
    if not script_name or not frappe.db.exists("ParentCallConfig", script_name):
        return {}
    doc = frappe.get_doc("ParentCallConfig", script_name)
    return {
        "name": doc.name,
        "title": getattr(doc, "title", doc.name),
        "status_text": getattr(doc, "status_template", "") or "",
        "is_active": getattr(doc, "is_active", 1)
    }


@frappe.whitelist()
def save_script(title, status_template):
    """Allow saving a newly designed script directly as a ParentCallConfig from the testing page."""
    if not title or not status_template:
        frappe.throw("Title and status template are required.")
    
    if frappe.db.exists("ParentCallConfig", title):
        doc = frappe.get_doc("ParentCallConfig", title)
        doc.status_template = status_template
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return {"success": True, "action": "updated", "name": doc.name}
    else:
        doc = frappe.get_doc({
            "doctype": "ParentCallConfig",
            "title": title,
            "status_template": status_template,
            "is_active": 1
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"success": True, "action": "created", "name": doc.name}


@frappe.whitelist()
def resolve_agent(language=None):
    """Helper to resolve agent ID based on language."""
    settings = _get_voice_agent_settings()
    if not settings:
        return ""
    return _resolve_agent_id(settings, language)


@frappe.whitelist()
def launch_test_call(
    phone,
    contact_name="Test Student",
    language="English",
    script_name=None,
    custom_variables="{}",
    custom_status_text=None,
    custom_welcome_message=None,
    agent_id_override=None,
    prospect_id_override=None
):
    """
    Launch a single test call directly via Vocallabs API.
    Handles contact registration / lookup, dynamic payload generation, and call dispatch.
    """
    settings = _get_voice_agent_settings()
    if not settings or not getattr(settings, "enabled", False):
        return {
            "success": False,
            "error": "Vocallabs integration is disabled in VoiceAgentSettings."
        }

    # Normalize phone
    raw_phone = str(phone).strip()
    digits = re.sub(r"\D", "", raw_phone)
    if not digits:
        return {"success": False, "error": "Invalid phone number provided."}
    if len(digits) == 10:
        clean_phone = f"+91{digits}"
    elif len(digits) == 12 and digits.startswith("91"):
        clean_phone = f"+{digits}"
    else:
        clean_phone = f"+{digits}" if not raw_phone.startswith("+") else raw_phone

    # Parse template variables
    try:
        var_dict = json.loads(custom_variables) if isinstance(custom_variables, str) else (custom_variables or {})
    except Exception:
        var_dict = {}

    # Defaults for variables
    var_dict.setdefault("student_name", contact_name)
    var_dict.setdefault("week", "1")
    var_dict.setdefault("reminder_count", "1")
    var_dict.setdefault("task_name", "Summer Activity")
    var_dict.setdefault("grace_deadline", "Sunday 8 PM")
    var_dict.setdefault("streak_count", "3")
    var_dict.setdefault("escalation_order", "1")

    # Render status_text prompt
    status_text = ""
    if custom_status_text:
        status_text = custom_status_text
    elif script_name and frappe.db.exists("ParentCallConfig", script_name):
        cfg = frappe.get_doc("ParentCallConfig", script_name)
        status_text = getattr(cfg, "status_template", "") or getattr(cfg, "status_text", "") or ""
    else:
        # Fallback generic prompt
        status_text = "Your child {student_name} is in week {week} of the TAP Summer Program. Please encourage them to complete this week's task. Thank you."

    # Format variables into status_text
    for k, v in var_dict.items():
        status_text = status_text.replace(f"{{{k}}}", str(v))

    # Render welcome message
    welcome_text = custom_welcome_message or "TAP Buddy"
    for k, v in var_dict.items():
        welcome_text = welcome_text.replace(f"{{{k}}}", str(v))

    # Resolve agent ID
    if agent_id_override and str(agent_id_override).strip():
        agent_id = str(agent_id_override).strip()
    else:
        agent_id = _resolve_agent_id(settings, language)

    if not agent_id:
        return {"success": False, "error": f"No agent ID configured for language '{language}'."}

    token = _get_auth_token(settings)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    service_url = settings.service_url.rstrip("/")

    def safe_post(url, payload):
        resp = requests.post(url, json=payload, headers=headers, timeout=25)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
        data = resp.json()
        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(f"{data.get('error')}: {data.get('message', '')}")
        return data

    def lookup_prospect_id(target_phone):
        """Reuse production getContacts pagination (vocallabs_prospects shape)."""
        return _lookup_prospect_id_by_phone(
            service_url,
            headers,
            settings.client_id,
            settings.default_contact_group_id,
            target_phone,
        )

    # Step 1: Resolve / Register Prospect
    try:
        prospect_id = str(prospect_id_override).strip() if (prospect_id_override and str(prospect_id_override).strip()) else None

        # Check local Redis cache
        cache_digits = re.sub(r"\D", "", clean_phone)[-10:]
        cache_key = f"vocallabs:phone_prospect:{cache_digits}"
        if not prospect_id:
            cached = frappe.cache().get_value(cache_key)
            if cached:
                prospect_id = str(cached)

        # Check existing Student record in DB
        existing_student = None
        if not prospect_id:
            existing_student = frappe.db.get_value(
                "Student",
                {"phone": ["like", f"%{cache_digits}"]},
                ["name", "vocallabs_prospect_id"],
                as_dict=True
            )
            if existing_student and existing_student.vocallabs_prospect_id:
                prospect_id = existing_student.vocallabs_prospect_id

        # Data block for Vocallabs
        parent_display = f"Parent of {contact_name}" if contact_name else "Parent"
        data_block = {
            "contact": parent_display,
            "student_name": contact_name,
            "status": status_text,
            "language": language or "English",
            "archetype": "Default",
            "experiment_arm": "Test",
            "welcome_greeting": welcome_text,
            "welcome_message": welcome_text
        }

        # If not known, register or search remote
        if not prospect_id:
            add_payload = {
                "prospects": [
                    {
                        "name": parent_display,
                        "phone": clean_phone,
                        "data": data_block,
                        "prospect_group_id": settings.default_contact_group_id or "",
                        "client_id": settings.client_id or "",
                    }
                ]
            }
            try:
                add_resp = safe_post(f"{service_url}/b2b/vocallabs/addMultipleContactsToGroup", add_payload)
                prospect_id = _extract_prospect_id(add_resp)
                if not prospect_id and _is_duplicate_prospect_response(add_resp):
                    prospect_id = lookup_prospect_id(clean_phone)
            except Exception:
                prospect_id = lookup_prospect_id(clean_phone)

            if not prospect_id:
                prospect_id = lookup_prospect_id(clean_phone)

        if not prospect_id:
            raise RuntimeError(f"Could not register or find phone {clean_phone} in Vocallabs contact group.")

        # Cache prospect ID in Redis
        frappe.cache().set_value(cache_key, prospect_id, expires_in_sec=86400 * 30)

        # Update contact data with current test parameters (ALWAYS refresh before call)
        try:
            update_resp = safe_post(f"{service_url}/b2b/vocallabs/updateContactData", {
                "prospect_id": prospect_id,
                "data": data_block
            })
            frappe.logger().info(f"Vocallabs updateContactData response: {update_resp}")
        except Exception as update_err:
            frappe.logger().warning(f"Vocallabs updateContactData warning: {update_err}")

        # Store on student if student exists
        if existing_student and prospect_id:
            frappe.db.set_value("Student", existing_student.name, "vocallabs_prospect_id", prospect_id)

        # 2. Initiate Call
        call_response = safe_post(f"{service_url}/b2b/vocallabs/initiateVocallabsCall", {
            "agentId": agent_id,
            "prospect_id": prospect_id
        })

        # 3. Log event if student and enrollment exist (safely)
        try:
            if existing_student:
                enrollment = frappe.db.get_value("ProgramEnrollment", {"student": existing_student.name}, ["name", "batch"], as_dict=True)
                if enrollment and enrollment.name and enrollment.batch:
                    frappe.get_doc({
                        "doctype": "ProgramEventLog",
                        "enrollment": enrollment.name,
                        "student": existing_student.name,
                        "batch": enrollment.batch,
                        "program_type": "Summer",
                        "event_type": "escalation_sent",
                        "trigger_source": "admin",
                        "created_at": now_datetime(),
                        "details": json.dumps({
                            "channel": "parent_call_test",
                            "phone": clean_phone,
                            "contact_name": contact_name,
                            "language": language,
                            "agent_id": agent_id,
                            "prospect_id": prospect_id,
                            "script_name": script_name,
                            "rendered_status": status_text,
                            "response": call_response
                        })
                    }).insert(ignore_permissions=True)
        except Exception:
            pass

        # Clear any spurious validation error messages so UI stays clean
        frappe.clear_messages()

        return {
            "success": True,
            "message": "Call initiated successfully via Vocallabs!",
            "phone": clean_phone,
            "agent_id": agent_id,
            "prospect_id": prospect_id,
            "rendered_status": status_text,
            "call_response": call_response
        }

    except Exception as e:
        frappe.log_error(message=f"Vocallabs Test Call failed: {str(e)}", title="SP Vocallabs Test Call")
        return {
            "success": False,
            "error": str(e),
            "phone": clean_phone,
            "agent_id": agent_id if 'agent_id' in locals() else "",
            "rendered_status": status_text if 'status_text' in locals() else ""
        }
