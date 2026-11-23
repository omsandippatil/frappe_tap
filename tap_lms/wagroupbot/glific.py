import datetime
import json

import frappe
import requests
from dateutil.parser import parse as parse_dt
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tap_lms.wagroupbot.redis_lock import (
    check_circuit_breaker,
    record_api_failure,
    record_api_success,
)

SETTINGS_DOCTYPE = "WA Bot Settings"
GRAPHQL_PATH = "/api/v1/graphql"


class GlificTerminalError(Exception):
    pass


class GlificAPIError(Exception):
    pass


class GlificManualTokenError(Exception):
    pass


ALLOWED_OPERATIONS = {
    "TestConnectionPing",
    "WaGroups",
    "WaManagedPhones",
    "WaGroupCollections",
    "WaPolls",
    "SendMessageInWaGroup",
    "CreateMessageMedia",
    "StartWaGroupFlow",
    "CreateWaPoll",
}

READ_ONLY_OPERATIONS = {
    "TestConnectionPing",
    "WaGroups",
    "WaManagedPhones",
    "WaGroupCollections",
    "WaPolls",
}

MEDIA_SEND_TYPES = {"IMAGE", "VIDEO", "DOCUMENT", "AUDIO"}

# Confirmed against this Glific instance's own schema via introspection on
# WaMessageResult, WaMessageInput, MessageMediaInput and MessageMediaResult:
#
# - WaMessageResult (the result of sendMessageInWaGroup and
#   startWaGroupFlow) exposes only `errors`. There is no `message`,
#   `success`, `id`, or `uuid` field on it at all — "no errors" is the only
#   success signal Glific gives back for a WA-group send. No
#   glific_message_id / our_message_uuid can ever be read from this
#   mutation's result; BQ-echo reconciliation in inbound.py remains the
#   sole source of truth for whether a WA-group send actually landed.
# - MessageMediaInput wants `sourceUrl` (not `url`) as the field carrying
#   the fetchable media URL; passing it as `url` is accepted by GraphQL
#   validation but rejected by Glific's own changeset with
#   "Source_url: can't be blank", since `source_url` is a required field on
#   the underlying MessageMedia record.
# - MessageMediaResult exposes `messageMedia { id }` (among other fields)
#   and `errors`, so the created media's id can be read back safely.


def normalize_phone(phone):
    phone = str(phone).replace("+", "").replace(" ", "").replace("-", "").strip()
    if phone.startswith("91"):
        return phone
    if len(phone) == 10:
        return "91" + phone
    return phone


def to_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)
    if isinstance(value, datetime.date):
        return datetime.datetime(value.year, value.month, value.day, tzinfo=datetime.timezone.utc)
    try:
        parsed = parse_dt(str(value))
    except Exception:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)


def _serialize_graphql_errors(errors):
    if isinstance(errors, list):
        messages = [e.get("message") for e in errors if isinstance(e, dict) and e.get("message")]
        if messages:
            return "; ".join(messages)
    if isinstance(errors, dict):
        message = errors.get("message")
        if message:
            return message
    return json.dumps(errors)


def _coerce_glific_id(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _coerce_glific_int_id(value, field_label):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise GlificTerminalError(
            f"{field_label} must resolve to a numeric Glific ID, got {value!r}. "
            f"A UUID or non-numeric value cannot be sent as this field."
        )


def _manual_token_blocked_error():
    return GlificManualTokenError(
        "Manual Glific Access Token has expired or is invalid. Auto token refresh is permanently "
        "disabled for this integration — paste a fresh Access Token into WA Bot Settings by hand."
    )


def _set_settings_values(values):
    try:
        frappe.db.set_single_value(SETTINGS_DOCTYPE, values)
    except Exception:
        frappe.log_error(
            title="WAGroupBot settings update failed",
            message=f"values={values}: {frappe.get_traceback()}",
        )


class GlificClient:
    def __init__(self):
        settings = frappe.get_single(SETTINGS_DOCTYPE)
        if not settings.glific_base_url:
            frappe.throw("Glific Base URL must be configured in WA Bot Settings.")

        self.graphql_url = settings.glific_base_url.rstrip("/") + GRAPHQL_PATH
        self.access_token = settings.get_password("access_token", raise_exception=False)

        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
            backoff_factor=1,
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.headers = {
            "Authorization": self.access_token or "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def ensure_valid_token(self):
        if not self.access_token:
            raise _manual_token_blocked_error()

    def _graphql_request(self, operation, query, variables=None, timeout=15):
        if operation not in ALLOWED_OPERATIONS:
            raise GlificTerminalError(f"GraphQL operation '{operation}' is not in the allow-list.")

        if check_circuit_breaker("glific"):
            raise GlificAPIError("Glific circuit breaker is open. Temporarily unavailable.")

        self.ensure_valid_token()
        payload = {"query": query, "variables": variables or {}}
        headers = dict(self.headers)
        is_read_only = operation in READ_ONLY_OPERATIONS

        try:
            if is_read_only:
                response = self.session.post(self.graphql_url, headers=headers, json=payload, timeout=timeout)
            else:
                response = requests.post(self.graphql_url, headers=headers, json=payload, timeout=timeout)

            if response.status_code == 401:
                _set_settings_values({
                    "last_sync_status": "Failed",
                    "last_sync_message": "Manual Glific Access Token has expired or is invalid. "
                                          "Paste a fresh Access Token into WA Bot Settings by hand.",
                    "last_sync_at": frappe.utils.now_datetime(),
                })
                frappe.db.commit()
                raise _manual_token_blocked_error()

            response.raise_for_status()
            data = response.json() if response.text else {}
            errors = data.get("errors")
            if errors:
                record_api_failure("glific")
                raise GlificTerminalError(_serialize_graphql_errors(errors))

            record_api_success("glific")
            return data.get("data", {})

        except GlificManualTokenError:
            raise
        except requests.exceptions.HTTPError as e:
            record_api_failure("glific")
            status_code = getattr(e.response, "status_code", 500)
            text = getattr(e.response, "text", str(e))
            if status_code in (400, 401, 404):
                raise GlificTerminalError(f"{status_code} - {text}")
            raise GlificAPIError(f"{status_code} - {text}")
        except requests.exceptions.RequestException as e:
            record_api_failure("glific")
            raise GlificAPIError(str(e))

    def test_connection(self):
        try:
            result = self._graphql_request(
                "TestConnectionPing",
                "query TestConnectionPing { users { id name } }",
            )
            if "users" in result:
                return {"status": "success", "message": "Successfully connected to Glific API."}
            return {"status": "failed", "message": "Unexpected response format."}
        except GlificManualTokenError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}


def get_wa_groups(client, limit=50, offset=0):
    query = """
    query WaGroups($opts: Opts) {
      waGroups(opts: $opts) {
        id
        label
        bspId
        lastCommunicationAt
        primaryPhone { id phone }
      }
    }
    """
    result = client._graphql_request("WaGroups", query, {"opts": {"limit": limit, "offset": offset, "order": "ASC"}})
    return result.get("waGroups") or []


def get_all_wa_groups(client, page_size=50):
    all_rows = []
    offset = 0
    while True:
        batch = get_wa_groups(client, limit=page_size, offset=offset)
        if not batch:
            break
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return all_rows


def list_wa_polls(client, limit=100):
    query = """
    query WaPolls($opts: Opts) {
      waPolls(opts: $opts) {
        id
        uuid
        label
        allowMultipleAnswer
      }
    }
    """
    result = client._graphql_request("WaPolls", query, {"opts": {"limit": limit, "order": "DESC"}})
    return result.get("waPolls") or []


def get_wa_managed_phones(client):
    query = """
    query WaManagedPhones {
      wa_managed_phones {
        id
        phone
        phone_id
        status
      }
    }
    """
    result = client._graphql_request("WaManagedPhones", query)
    return result.get("wa_managed_phones") or []


def get_wa_group_collections(client, limit=50, offset=0):
    query = """
    query WaGroupCollections($opts: Opts) {
      groups(opts: $opts) { id label waGroupsCount }
    }
    """
    result = client._graphql_request("WaGroupCollections", query, {"opts": {"limit": limit, "offset": offset, "order": "ASC"}})
    return result.get("groups") or []


def get_all_wa_group_collections(client, page_size=50):
    all_rows = []
    offset = 0
    while True:
        batch = get_wa_group_collections(client, limit=page_size, offset=offset)
        if not batch:
            break
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return all_rows


def send_message_to_wa_group(client, wa_group_id, message, phone_id=None, media_id=None,
                              msg_type="TEXT", poll_id=None):
    if media_id is not None and msg_type == "TEXT":
        raise GlificTerminalError(
            "media_id set but msg_type is TEXT — refusing a malformed media send. "
            "Pass the matching Glific media type (IMAGE/VIDEO/DOCUMENT/AUDIO)."
        )

    query = """
    mutation SendMessageInWaGroup($input: WaMessageInput!) {
      sendMessageInWaGroup(input: $input) {
        errors { key message }
      }
    }
    """
    input_payload = {
        "waGroupId": str(_coerce_glific_id(wa_group_id)),
        "message": message or "",
        "type": msg_type,
    }
    if media_id is not None:
        input_payload["mediaId"] = str(_coerce_glific_id(media_id))
    if phone_id is not None:
        input_payload["waManagedPhoneId"] = str(_coerce_glific_id(phone_id))
    if poll_id is not None:
        input_payload["pollId"] = _coerce_glific_int_id(poll_id, "pollId")

    variables = {"input": input_payload}
    result = client._graphql_request("SendMessageInWaGroup", query, variables).get("sendMessageInWaGroup") or {}
    errors = result.get("errors")
    if errors:
        raise GlificTerminalError(_serialize_graphql_errors(errors))

    # WaMessageResult has no id/uuid/success field on this Glific instance
    # (confirmed via introspection) — absence of errors is the only success
    # signal available here. Callers must tolerate an empty message dict
    # and must not treat it as a failed send; glific_message_id and
    # our_message_uuid stay blank for WA-group sends, by design, until
    # Glific's schema exposes something to read back.
    return {"message": {}}


def send_poll_to_wa_group(client, wa_group_id, glific_poll_id, phone_id=None):
    if not glific_poll_id:
        raise GlificTerminalError(
            "send_poll_to_wa_group called without a numeric glific_poll_id. "
            "A poll UUID cannot be sent directly — resolve glific_poll_id via WA Poll Label first."
        )
    numeric_poll_id = _coerce_glific_int_id(glific_poll_id, "pollId")
    return send_message_to_wa_group(
        client, wa_group_id, message="", phone_id=phone_id, msg_type="POLL", poll_id=numeric_poll_id,
    )


def create_message_media(client, url, caption=None, media_type="IMAGE"):
    if media_type not in MEDIA_SEND_TYPES:
        raise GlificTerminalError(
            f"Unknown media_type {media_type!r}, expected one of {sorted(MEDIA_SEND_TYPES)}."
        )
    if not url:
        raise GlificTerminalError(
            "create_message_media called with no url — refusing to send an empty source url to Glific."
        )

    query = """
    mutation CreateMessageMedia($input: MessageMediaInput!) {
      createMessageMedia(input: $input) {
        messageMedia { id }
        errors { key message }
      }
    }
    """
    input_payload = {"sourceUrl": url, "url": url}
    if caption:
        input_payload["caption"] = caption
    variables = {"input": input_payload}
    result = client._graphql_request("CreateMessageMedia", query, variables).get("createMessageMedia") or {}
    errors = result.get("errors")
    if errors:
        raise GlificTerminalError(_serialize_graphql_errors(errors))
    media = result.get("messageMedia")
    if not media or not media.get("id"):
        raise GlificTerminalError("Glific did not return a media id for this upload.")
    return media


def start_wa_group_flow(client, wa_group_id, flow_id):
    query = """
    mutation StartWaGroupFlow($waGroupId: ID!, $flowId: ID!) {
      startWaGroupFlow(waGroupId: $waGroupId, flowId: $flowId) {
        success
        errors { key message }
      }
    }
    """
    variables = {
        "waGroupId": str(_coerce_glific_id(wa_group_id)),
        "flowId": str(_coerce_glific_id(flow_id)),
    }
    result = client._graphql_request("StartWaGroupFlow", query, variables).get("startWaGroupFlow") or {}
    errors = result.get("errors")
    if errors:
        raise GlificTerminalError(_serialize_graphql_errors(errors))
    if result.get("success") is False:
        raise GlificTerminalError("Glific reported success=false for startWaGroupFlow with no error detail.")
    return result


def create_wa_poll(client, label, poll_content_json, allow_multiple_answer):
    query = """
    mutation CreateWaPoll($input: WaPollInput!) {
      createWaPoll(input: $input) {
        waPoll { id uuid label allowMultipleAnswer }
        errors { key message }
      }
    }
    """
    variables = {
        "input": {
            "label": label,
            "pollContent": poll_content_json,
            "allowMultipleAnswer": bool(allow_multiple_answer),
        }
    }
    result = client._graphql_request("CreateWaPoll", query, variables).get("createWaPoll") or {}
    errors = result.get("errors")
    if errors:
        raise GlificTerminalError(_serialize_graphql_errors(errors))
    poll = result.get("waPoll")
    if not poll or not poll.get("id") or not poll.get("uuid"):
        raise GlificTerminalError("Glific did not return a complete poll record (id/uuid missing).")
    return poll