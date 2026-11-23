import mimetypes

import frappe
import requests

from tap_lms.wagroupbot.redis_lock import register_media_cache_key, clear_media_cache, MEDIA_CACHE_MAX_ENTRIES

CACHE_PREFIX = "wagroupbot:media_proxy:"
CACHE_TTL_SECONDS = 3600
MAX_CACHEABLE_BYTES = 5 * 1024 * 1024
FETCH_TIMEOUT_SECONDS = 15


def _emit_bytes(content, content_type, filename_hint=None):
    content_type = content_type or "application/octet-stream"
    if not filename_hint:
        ext = mimetypes.guess_extension(content_type) or ""
        filename_hint = f"media{ext}"
    frappe.local.response.filename = filename_hint
    frappe.local.response.filecontent = content
    frappe.local.response.type = "download"
    frappe.local.response.content_type = content_type


def _emit_error(status_code, message=""):
    frappe.local.response.http_status_code = status_code
    frappe.local.response["message"] = message


@frappe.whitelist()
def get_media(media_name=None, turn_name=None, item_bq_id=None):
    try:
        _run(media_name=media_name, turn_name=turn_name, item_bq_id=item_bq_id)
    except frappe.PermissionError:
        _emit_error(403, "Not permitted")
    except Exception:
        frappe.logger("wagroupbot_media_proxy").warning(
            f"Unhandled error for media_name={media_name} turn_name={turn_name} "
            f"item_bq_id={item_bq_id}: {frappe.get_traceback()}"
        )
        _emit_error(502, "Media proxy error")


def _run(media_name=None, turn_name=None, item_bq_id=None):
    if frappe.session.user == "Guest":
        frappe.throw("Not permitted", frappe.PermissionError)
    frappe.only_for("System Manager")

    bq_id = media_name or item_bq_id
    if not bq_id:
        _emit_error(400, "Missing bq_id")
        return

    cache_key = f"{CACHE_PREFIX}{bq_id}"
    cache = frappe.cache()

    try:
        cached = cache.get_value(cache_key)
    except Exception:
        cached = None

    if cached:
        try:
            cached_type = cache.get_value(f"{cache_key}:type") or "application/octet-stream"
        except Exception:
            cached_type = "application/octet-stream"
        _emit_bytes(cached, cached_type, filename_hint=str(bq_id))
        return

    url, mime = _resolve_media_url(bq_id, turn_name)
    if not url:
        frappe.logger("wagroupbot_media_proxy").info(
            f"No media URL resolved for bq_id={bq_id} turn_name={turn_name}"
        )
        _emit_error(404, "Media not available for this item")
        return

    try:
        response = requests.get(url, timeout=FETCH_TIMEOUT_SECONDS, stream=True)
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length and content_length.isdigit() and int(content_length) > MAX_CACHEABLE_BYTES:
            response.close()
            _emit_error(413, "Media too large to proxy")
            return

        content = bytearray()
        for chunk in response.iter_content(chunk_size=1024 * 64):
            content.extend(chunk)
            if len(content) > MAX_CACHEABLE_BYTES:
                response.close()
                _emit_error(413, "Media too large to proxy")
                return
        content = bytes(content)
    except Exception as e:
        frappe.logger("wagroupbot_media_proxy").warning(
            f"Fetch failed for bq_id={bq_id} url={url}: {e}"
        )
        _emit_error(502, "Upstream fetch failed")
        return

    content_type = response.headers.get("Content-Type") or _guess_content_type(mime)

    try:
        cache.set_value(cache_key, content, expires_in_sec=CACHE_TTL_SECONDS)
        cache.set_value(f"{cache_key}:type", content_type, expires_in_sec=CACHE_TTL_SECONDS)
        register_media_cache_key(cache_key, max_entries=MEDIA_CACHE_MAX_ENTRIES)
    except Exception:
        frappe.log_error(title="WAGroupBot media cache write failed", message=f"bq_id={bq_id}: {frappe.get_traceback()}")

    _emit_bytes(content, content_type, filename_hint=str(bq_id))


def _guess_content_type(mime):
    mime = (mime or "").lower()
    if mime == "image":
        return "image/jpeg"
    if mime == "video":
        return "video/mp4"
    if mime == "sticker":
        return "image/webp"
    return "application/octet-stream"


def _resolve_media_url(bq_id, turn_name=None):
    row = frappe.db.get_value(
        "WA Media",
        {"bq_id": bq_id},
        ["media_gcs_url", "media_mime_type"],
        as_dict=True,
    )
    if row and row.media_gcs_url:
        return row.media_gcs_url, row.media_mime_type

    item_filters = {"bq_id": bq_id, "parenttype": "WA Group Turn"}
    if turn_name:
        item_filters["parent"] = turn_name
    item = frappe.db.get_value(
        "WA Group Turn Item", item_filters,
        ["media_gcs_url", "media_mime_type"], as_dict=True,
    )
    if item and item.media_gcs_url:
        return item.media_gcs_url, item.media_mime_type

    return None, None


@frappe.whitelist()
def purge_media_cache():
    """Drops the entire media proxy cache right now. Called from
    api.purge_dashboard_cache when the dashboard is closing — there's no
    point keeping cached media around once nobody's viewing it."""
    frappe.only_for("System Manager")
    cleared = clear_media_cache()
    return {"status": "ok", "cleared": cleared}