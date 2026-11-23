import mimetypes
import secrets

import frappe
from frappe.utils import now_datetime, add_to_date, get_url

SETTINGS_DOCTYPE = "WA Bot Settings"
TOKEN_BYTES = 32
ENDPOINT_PATH = "/api/method/tap_lms.wagroupbot.media_outbound.get_outbound_media"

MIME_PREFIX_TO_GLIFIC_TYPE = {
    "image": "image",
    "video": "video",
    "audio": "audio",
}


def _ttl_minutes(settings=None):
    settings = settings or frappe.get_cached_doc(SETTINGS_DOCTYPE)
    return settings.media_public_url_ttl_minutes or 180


def mint_media_token(file_url, ttl_minutes=None, settings=None):
    ttl_minutes = ttl_minutes or _ttl_minutes(settings)
    existing = frappe.db.sql(
        """
        SELECT token
        FROM "tabWA Media Token"
        WHERE file_url = %(file_url)s AND expires_at > %(now)s
        ORDER BY expires_at DESC
        LIMIT 1
        """,
        {"file_url": file_url, "now": now_datetime()},
        as_dict=True,
    )
    if existing:
        return existing[0].token

    token = secrets.token_urlsafe(TOKEN_BYTES)
    expires_at = add_to_date(now_datetime(), minutes=ttl_minutes)
    frappe.db.sql(
        """
        INSERT INTO "tabWA Media Token"
            (name, token, file_url, expires_at, creation, modified, owner, modified_by)
        VALUES
            (%(token)s, %(token)s, %(file_url)s, %(expires_at)s, now(), now(), %(user)s, %(user)s)
        """,
        {
            "token": token,
            "file_url": file_url,
            "expires_at": expires_at,
            "user": frappe.session.user,
        },
    )
    frappe.db.commit()
    return token


def build_outbound_media_url(file_url, ttl_minutes=None, settings=None):
    token = mint_media_token(file_url, ttl_minutes=ttl_minutes, settings=settings)
    return f"{get_url()}{ENDPOINT_PATH}?token={token}"


def detect_media_type(file_url):
    if not file_url:
        return "document"
    content_type = frappe.db.get_value("File", {"file_url": file_url}, "content_type") or ""
    prefix = content_type.split("/")[0].strip().lower()
    return MIME_PREFIX_TO_GLIFIC_TYPE.get(prefix, "document")


def resolve_outbound_media_url(doc, file_field="media_file", url_field="media_url", settings=None, max_mb=None):
    file_value = doc.get(file_field)
    url_value = doc.get(url_field)

    if file_value:
        if max_mb:
            size = frappe.db.get_value("File", {"file_url": file_value}, "file_size") or 0
            if size > max_mb * 1024 * 1024:
                frappe.throw(f"Attached media exceeds the {max_mb} MB upload limit.")
        return build_outbound_media_url(file_value, settings=settings)

    if url_value:
        return url_value

    frappe.throw("No media file or media URL is set on this record.")


def _emit_error(status_code, message=""):
    frappe.local.response.http_status_code = status_code
    frappe.local.response["message"] = message


@frappe.whitelist(allow_guest=True)
def get_outbound_media(token=None):
    try:
        _run(token)
    except Exception:
        frappe.logger("wagroupbot_media_outbound").warning(
            f"Unhandled error for token={token}: {frappe.get_traceback()}"
        )
        _emit_error(502, "Media outbound proxy error")


def _run(token):
    if not token:
        _emit_error(400, "Missing token")
        return

    row = frappe.db.sql(
        """
        SELECT name, file_url, expires_at, first_fetched_at
        FROM "tabWA Media Token"
        WHERE token = %(token)s
        LIMIT 1
        """,
        {"token": token},
        as_dict=True,
    )
    if not row:
        _emit_error(404, "Token not found")
        return

    record = row[0]
    if record.expires_at < now_datetime():
        _emit_error(410, "Token expired")
        return

    file_name = frappe.db.get_value("File", {"file_url": record.file_url}, "name")
    if not file_name:
        _emit_error(404, "File not found")
        return

    file_doc = frappe.get_doc("File", file_name)
    try:
        content = file_doc.get_content()
    except OSError:
        _emit_error(404, "File unreadable")
        return

    if not record.first_fetched_at:
        frappe.db.sql(
            'UPDATE "tabWA Media Token" SET first_fetched_at = %(now)s WHERE name = %(name)s',
            {"now": now_datetime(), "name": record.name},
        )
        frappe.db.commit()

    frappe.local.response.filename = file_doc.file_name
    frappe.local.response.filecontent = content
    frappe.local.response.type = "download"
    frappe.local.response.content_type = file_doc.content_type or mimetypes.guess_type(file_doc.file_name)[0] or "application/octet-stream"