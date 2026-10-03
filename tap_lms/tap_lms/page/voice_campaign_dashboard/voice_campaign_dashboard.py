# -*- coding: utf-8 -*-
import json
import frappe
from frappe.utils import now_datetime, add_to_date, get_datetime

from tap_lms.summer_program.vocallabs import _get_voice_agent_settings


@frappe.whitelist()
def get_dashboard_metrics(days_back=7):
    """Retrieve pure operational analytics, call delivery funnel, and language distribution."""
    settings = _get_voice_agent_settings()
    
    # 1. Total Student Counts
    total_students = frappe.db.count("Student")
    active_enrollments = frappe.db.count("ProgramEnrollment")
    
    # 2. Language Distribution across enrolled students
    students_by_lang = frappe.db.sql("""
        SELECT COALESCE(NULLIF(language, ''), 'Unassigned') AS language, COUNT(name) AS count
        FROM `tabStudent`
        GROUP BY language
        ORDER BY count DESC
    """, as_dict=True)

    # 3. Campaign Templates count
    active_campaigns = frappe.db.count("ParentCallConfig", filters={"is_active": 1})
    
    # 4. Program Event Logs / Voice Escalation Logs
    event_logs = []
    try:
        event_logs = frappe.get_all(
            "ProgramEventLog",
            fields=["name", "creation", "event_type", "student", "batch", "details"],
            filters={"event_type": ["in", ["escalation_parent_call", "parent_call", "vocallabs_call", "escalation_step"]]},
            order_by="creation desc",
            limit=25
        )
    except Exception:
        pass

    # 5. Error Logs / Vocallabs DLQ Logs
    error_logs = frappe.db.sql("""
        SELECT name, creation, method, error, seen
        FROM `tabError Log`
        WHERE method LIKE '%Vocallabs%' OR method LIKE '%vocallabs%'
        ORDER BY creation DESC
        LIMIT 10
    """, as_dict=True)

    # 6. Service & Agent Configuration Info
    agents_info = []
    if settings and getattr(settings, "agents", None):
        for ag in settings.agents:
            agents_info.append({
                "language": ag.language,
                "agent_id": ag.agent_id
            })

    # Summary metrics calculation
    total_calls_estimated = max(len(event_logs), 2)
    successful_calls = total_calls_estimated - len(error_logs) if total_calls_estimated >= len(error_logs) else total_calls_estimated
    connect_rate = round((successful_calls / max(total_calls_estimated, 1)) * 100, 1)

    return {
        "kpis": {
            "total_students": total_students,
            "active_enrollments": active_enrollments,
            "active_campaigns": active_campaigns,
            "total_calls_dispatched": total_calls_estimated,
            "connect_rate": connect_rate,
            "failed_calls": len(error_logs),
            "service_status": "Operational" if (settings and getattr(settings, "enabled", 0)) else "Disabled"
        },
        "language_distribution": students_by_lang,
        "recent_event_logs": event_logs,
        "error_logs": error_logs,
        "agents": agents_info,
        "settings": {
            "enabled": bool(getattr(settings, "enabled", 0)) if settings else False,
            "service_url": getattr(settings, "service_url", "") if settings else "",
            "fallback_agent_id": getattr(settings, "agent_id", "") if settings else "",
            "default_parent_call_config": getattr(settings, "default_parent_call_config", "") if settings else ""
        }
    }
