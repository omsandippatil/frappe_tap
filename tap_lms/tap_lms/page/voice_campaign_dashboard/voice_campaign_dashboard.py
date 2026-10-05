# -*- coding: utf-8 -*-
import json
import frappe
from frappe.utils import now_datetime, add_to_date, get_datetime

from tap_lms.summer_program.vocallabs import _get_voice_agent_settings

# ProgramEventLog types that are always voice/parent-call related.
_VOICE_OUTCOME_EVENT_TYPES = frozenset({
    "parent_call_outcome",
    "call_failed",
    "call_queued",
    "call_completed",
})

# Older dashboard filter names (keep so historic rows still appear).
_LEGACY_VOICE_EVENT_TYPES = frozenset({
    "escalation_parent_call",
    "parent_call",
    "vocallabs_call",
    "escalation_step",
})

_CONNECTED_STATUSES = frozenset({"completed", "complete", "answered"})


def _parse_details(details):
    if not details:
        return {}
    if isinstance(details, dict):
        return details
    try:
        return json.loads(details)
    except (TypeError, ValueError):
        return {}


def _is_parent_call_dispatch(event_type, details_raw):
    """True when escalation_sent (or legacy type) represents a Vocallabs hand-off."""
    if event_type in _LEGACY_VOICE_EVENT_TYPES:
        return True
    if event_type != "escalation_sent":
        return False
    d = _parse_details(details_raw)
    channel = (d.get("channel") or "").strip()
    if channel in ("parent_call", "parent_call_test"):
        return True
    if (d.get("escalation_type") or "").strip() == "parent_call":
        return True
    return False


def _log_summary_and_status(event_type, details_raw, trigger_source=None):
    """Human-readable row text + badge for the dashboard table."""
    d = _parse_details(details_raw)
    src = (trigger_source or "").strip()

    if event_type == "parent_call_outcome":
        status = (d.get("call_status") or "unknown").strip().lower()
        phone = d.get("phone_to") or ""
        summary = f"{status}"
        if phone:
            summary += f" · {phone}"
        if d.get("duration"):
            summary += f" · {d.get('duration')}s"
        if status in _CONNECTED_STATUSES:
            return summary, "Connected", "success"
        if status in ("no-answer", "busy", "fail", "failed", "canceled", "cancelled"):
            return summary, status.replace("-", " ").title(), "warning"
        return summary, status.title(), "secondary"

    if _is_parent_call_dispatch(event_type, details_raw):
        channel = d.get("channel") or "parent_call"
        if channel == "parent_call_test" or src == "admin":
            label = "Test dispatch"
        else:
            label = "Dispatched"
        order = d.get("escalation_order") or d.get("step")
        summary = f"Vocallabs {channel}"
        if order:
            summary += f" (step {order})"
        return summary, label, "info"

    if event_type == "call_failed":
        return d.get("reason") or "Call failed", "Failed", "danger"

    if event_type in ("call_queued", "call_completed"):
        return json.dumps(d, default=str)[:80] if d else event_type, event_type, "secondary"

    return (str(details_raw or event_type)[:80], event_type, "primary")


def _fetch_voice_events(since_dt, limit=50):
    """Load recent voice-related ProgramEventLog rows (filter in Python for JSON details)."""
    candidates = frappe.get_all(
        "ProgramEventLog",
        fields=[
            "name",
            "creation",
            "event_type",
            "student",
            "batch",
            "details",
            "trigger_source",
        ],
        filters={
            "creation": [">=", since_dt],
            "event_type": [
                "in",
                list(
                    _VOICE_OUTCOME_EVENT_TYPES
                    | _LEGACY_VOICE_EVENT_TYPES
                    | {"escalation_sent"}
                ),
            ],
        },
        order_by="creation desc",
        limit=500,
    )

    rows = []
    for row in candidates:
        et = row.get("event_type")
        if et in _VOICE_OUTCOME_EVENT_TYPES or et in _LEGACY_VOICE_EVENT_TYPES:
            include = True
        elif et == "escalation_sent":
            include = _is_parent_call_dispatch(et, row.get("details"))
        else:
            include = False
        if not include:
            continue
        summary, status_label, status_class = _log_summary_and_status(
            et, row.get("details"), row.get("trigger_source")
        )
        rows.append({
            "name": row.get("name"),
            "creation": row.get("creation"),
            "event_type": et,
            "student": row.get("student"),
            "batch": row.get("batch"),
            "trigger_source": row.get("trigger_source"),
            "summary": summary,
            "status_label": status_label,
            "status_class": status_class,
        })
        if len(rows) >= limit:
            break
    return rows


def _dispatch_dedupe_key(row):
    """One parent-call attempt can log twice (dispatcher + vocallabs success)."""
    d = _parse_details(row.get("details"))
    enrollment = row.get("enrollment") or row.get("student") or row.get("name")
    step = d.get("escalation_order") or d.get("step") or ""
    created = row.get("creation")
    minute = ""
    if created:
        try:
            minute = get_datetime(created).strftime("%Y-%m-%d %H:%M")
        except Exception:
            minute = str(created)[:16]
    return (enrollment, str(step), minute)


def _count_dispatches_and_outcomes(since_dt):
    """KPI counts for the selected time window."""
    rows = frappe.get_all(
        "ProgramEventLog",
        fields=["name", "enrollment", "student", "creation", "event_type", "details"],
        filters={
            "creation": [">=", since_dt],
            "event_type": [
                "in",
                list(
                    _VOICE_OUTCOME_EVENT_TYPES
                    | _LEGACY_VOICE_EVENT_TYPES
                    | {"escalation_sent"}
                ),
            ],
        },
        limit=0,
    )

    dispatch_keys = set()
    dispatches = 0
    outcomes = 0
    connected = 0

    for row in rows:
        et = row.get("event_type")
        details = row.get("details")
        if _is_parent_call_dispatch(et, details):
            key = _dispatch_dedupe_key(row)
            if key not in dispatch_keys:
                dispatch_keys.add(key)
                dispatches += 1
        elif et == "parent_call_outcome":
            outcomes += 1
            status = (_parse_details(details).get("call_status") or "").strip().lower()
            if status in _CONNECTED_STATUSES:
                connected += 1
        elif et == "call_completed":
            outcomes += 1
            connected += 1

    return dispatches, outcomes, connected


@frappe.whitelist()
def get_dashboard_metrics(days_back=7):
    """Operational voice metrics: real ProgramEventLog + Vocallabs Error Log."""
    settings = _get_voice_agent_settings()
    days_back = max(1, min(int(days_back or 7), 90))
    since_dt = add_to_date(now_datetime(), days=-days_back)

    total_students = frappe.db.count("Student")
    active_enrollments = frappe.db.count("ProgramEnrollment")

    students_by_lang = frappe.db.sql("""
        SELECT COALESCE(NULLIF(language, ''), 'Unassigned') AS language, COUNT(name) AS count
        FROM `tabStudent`
        GROUP BY language
        ORDER BY count DESC
    """, as_dict=True)

    active_campaigns = frappe.db.count("ParentCallConfig", filters={"is_active": 1})

    event_logs = _fetch_voice_events(since_dt, limit=50)
    dispatches, outcomes, connected = _count_dispatches_and_outcomes(since_dt)

    error_logs = frappe.db.sql("""
        SELECT name, creation, method, error, seen
        FROM `tabError Log`
        WHERE creation >= %s
          AND (method LIKE %s OR method LIKE %s OR error LIKE %s)
        ORDER BY creation DESC
        LIMIT 25
    """, (since_dt, "%Vocallabs%", "%vocallabs%", "%Vocallabs%"), as_dict=True)

    call_failed_events = frappe.db.count(
        "ProgramEventLog",
        filters={
            "creation": [">=", since_dt],
            "event_type": "call_failed",
        },
    )
    failed_calls = len(error_logs) + call_failed_events

    if outcomes > 0:
        connect_rate = round((connected / outcomes) * 100, 1)
    else:
        connect_rate = None

    agents_info = []
    if settings and getattr(settings, "agents", None):
        for ag in settings.agents:
            agents_info.append({
                "language": ag.language,
                "agent_id": ag.agent_id,
            })

    return {
        "days_back": days_back,
        "kpis": {
            "total_students": total_students,
            "active_enrollments": active_enrollments,
            "active_campaigns": active_campaigns,
            "total_calls_dispatched": dispatches,
            "outcomes_reported": outcomes,
            "connected_calls": connected,
            "connect_rate": connect_rate,
            "failed_calls": failed_calls,
            "service_status": "Operational" if (settings and getattr(settings, "enabled", 0)) else "Disabled",
        },
        "language_distribution": students_by_lang,
        "recent_event_logs": event_logs,
        "error_logs": error_logs,
        "agents": agents_info,
        "settings": {
            "enabled": bool(getattr(settings, "enabled", 0)) if settings else False,
            "service_url": getattr(settings, "service_url", "") if settings else "",
            "fallback_agent_id": getattr(settings, "agent_id", "") if settings else "",
            "default_parent_call_config": getattr(settings, "default_parent_call_config", "") if settings else "",
        },
    }
