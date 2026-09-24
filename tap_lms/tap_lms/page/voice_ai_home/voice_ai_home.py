# -*- coding: utf-8 -*-
import frappe
from tap_lms.summer_program.vocallabs import _get_voice_agent_settings


@frappe.whitelist()
def get_home_summary():
    """Retrieve counts and status overview for the Voice AI Home page."""
    settings = _get_voice_agent_settings()
    
    total_students = frappe.db.count("Student")
    total_scripts = frappe.db.count("ParentCallConfig", filters={"is_active": 1})
    total_enrollments = frappe.db.count("ProgramEnrollment")
    
    agents = []
    if settings and getattr(settings, "agents", None):
        for ag in settings.agents:
            agents.append({
                "language": ag.language,
                "agent_id": ag.agent_id
            })

    return {
        "total_students": total_students,
        "total_scripts": total_scripts,
        "total_enrollments": total_enrollments,
        "settings": {
            "enabled": bool(getattr(settings, "enabled", 0)) if settings else False,
            "service_url": getattr(settings, "service_url", "") if settings else "",
            "fallback_agent_id": getattr(settings, "agent_id", "") if settings else "",
            "default_script": getattr(settings, "default_parent_call_config", "") if settings else ""
        },
        "agents": agents
    }
