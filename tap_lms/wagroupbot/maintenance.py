import frappe
from frappe.utils import now_datetime

from tap_lms.wagroupbot.redis_lock import acquire_lock, trim_media_cache

MAINTENANCE_THROTTLE_KEY = "wagroupbot:maintenance:last_run"
MAINTENANCE_INTERVAL_SECONDS = 300


def run_if_due(force=False):
    cache = frappe.cache()
    if not force and cache.get_value(MAINTENANCE_THROTTLE_KEY):
        return {"status": "skipped"}

    if not acquire_lock("maintenance_run", timeout=60):
        return {"status": "skipped_locked"}

    result = {}

    try:
        from tap_lms.tap_lms.doctype.wa_media_token.wa_media_token import purge_expired as purge_tokens
        purge_tokens()
        result["tokens_purged"] = True
    except Exception:
        frappe.log_error(title="WAGroupBot maintenance: token purge failed", message=frappe.get_traceback())
        result["tokens_purged"] = False

    try:
        from tap_lms.tap_lms.doctype.wa_reaction_retry_queue.wa_reaction_retry_queue import purge_exhausted
        purge_exhausted()
        result["retry_queue_purged"] = True
    except Exception:
        frappe.log_error(title="WAGroupBot maintenance: retry queue purge failed", message=frappe.get_traceback())
        result["retry_queue_purged"] = False

    try:
        result["media_cache_evicted"] = trim_media_cache()
    except Exception:
        frappe.log_error(title="WAGroupBot maintenance: media cache trim failed", message=frappe.get_traceback())
        result["media_cache_evicted"] = 0

    cache.set_value(MAINTENANCE_THROTTLE_KEY, now_datetime().isoformat(), expires_in_sec=MAINTENANCE_INTERVAL_SECONDS)
    return {"status": "ran", **result}