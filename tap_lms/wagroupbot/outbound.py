import json
import re
import time

import frappe
from frappe.utils import now_datetime, add_to_date

from tap_lms.wagroupbot.glific import (
    GlificClient,
    GlificTerminalError,
    GlificManualTokenError,
    send_message_to_wa_group,
    create_message_media,
    start_wa_group_flow,
    send_poll_to_wa_group,
)
from tap_lms.wagroupbot.targeting import target_group_names, remaining_targets
from tap_lms.wagroupbot.media_outbound import resolve_outbound_media_url
from tap_lms.tap_lms.doctype.wa_bot_settings.wa_bot_settings import is_test_mode, get_effective_group
from tap_lms.tap_lms.doctype.wa_poll_label.wa_poll_label import get_glific_poll_id
from tap_lms.wagroupbot.queues import enqueue as _wag_enqueue, SEND_QUEUE
from tap_lms.wagroupbot.redis_lock import acquire_lock, release_lock

SETTINGS_DOCTYPE = "WA Bot Settings"
TURN_DOCTYPE = "WA Group Turn"
SEND_BATCH_DOCTYPE = "WA Send Batch"
SEND_MESSAGE_DOCTYPE = "WA Send Message"
SEND_SWEEP_BATCH_SIZE = 200
SEND_PACING_SECONDS = 2.1
AI_DRAFTABLE_ITEM_TYPES = {"Text", "Media", "Voice", "Poll Response"}
AUTO_REPLY_RULES_CACHE_KEY = "wagroupbot:active_auto_reply_rules"
AUTO_REPLY_RULES_CACHE_TTL = 180
RECENT_REPLY_COOLDOWN_SECONDS = 15
AUTO_REPLY_DISPATCH_GUARD_SECONDS = 15
TAG_PLACEHOLDER = "@{{tag}}"

MAX_SEND_BATCH_TARGET_GROUPS = 2000
SEND_INTENT_LOCK_SECONDS = 90


def _send_intent_key(batch_name, wave_number, group_name):
    return f"send_intent:{batch_name}:{wave_number}:{group_name}"


def preview_dispatch_targets(target_type, wa_group=None, wa_group_collection=None,
                              district=None, city=None, state=None, school=None, settings=None):
    settings = settings or frappe.get_cached_doc(SETTINGS_DOCTYPE)

    real_group_names = target_group_names(
        target_type, wa_group=wa_group, wa_group_collection=wa_group_collection,
        district=district, city=city, state=state, school=school,
    )

    if is_test_mode(settings):
        effective_names = [get_effective_group(None, settings)]
    else:
        effective_names = real_group_names

    label_rows = frappe.get_all(
        "WA Group", filters={"name": ["in", list(set(real_group_names + effective_names))]},
        fields=["name", "group_name"],
    )
    label_map = {r.name: r.group_name for r in label_rows}

    return {
        "mode": settings.bot_mode,
        "real_group_count": len(real_group_names),
        "real_groups": [{"name": n, "group_name": label_map.get(n, n)} for n in real_group_names],
        "effective_group_count": len(effective_names),
        "effective_groups": [{"name": n, "group_name": label_map.get(n, n)} for n in effective_names],
    }


def _resolve_poll_uuid_for_group(doc, group_name):
    if not doc.is_multi_language_poll:
        return doc.poll_uuid

    group_language = frappe.db.get_value("WA Group", group_name, "group_language")
    default_uuid = None
    for row in doc.poll_languages:
        if row.is_default:
            default_uuid = row.poll_uuid
        if group_language and row.language == group_language:
            return row.poll_uuid
    return default_uuid


def _already_sent_group_names(batch_name, wave_number=None):
    filters = {"batch": batch_name, "origin": "Batch Wave"}
    if wave_number is not None:
        filters["wave_number"] = wave_number
    return frappe.get_all(SEND_MESSAGE_DOCTYPE, filters=filters, pluck="wa_group")


def _ensure_test_group_still_valid(settings):
    if not is_test_mode(settings):
        return
    if not settings.test_wa_group:
        frappe.throw("Bot Mode is Test but no Test WA Group is configured in WA Bot Settings.")
    is_enabled = frappe.db.get_value("WA Group", settings.test_wa_group, "is_enabled")
    if not is_enabled:
        frappe.throw(
            f"Test WA Group {settings.test_wa_group} is disabled. While Bot Mode is Test, every "
            f"send is redirected here — enable this group or choose a different Test WA Group "
            f"before sending anything."
        )


def expand_send_batch(batch_name):
    doc = frappe.get_doc(SEND_BATCH_DOCTYPE, batch_name)
    settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
    _ensure_test_group_still_valid(settings)

    real_group_names = target_group_names(
        doc.target_type, wa_group=doc.wa_group, wa_group_collection=doc.wa_group_collection,
        district=doc.district, city=doc.city, state=doc.state, school=doc.school,
    )

    if is_test_mode(settings):
        effective_groups = [get_effective_group(None, settings)]
    else:
        effective_groups = real_group_names

    if not effective_groups:
        frappe.throw("No WA Groups resolved for this batch. Refusing to schedule an empty target.")

    if len(real_group_names) > MAX_SEND_BATCH_TARGET_GROUPS:
        frappe.throw(
            f"This batch resolved to {len(real_group_names)} WA Groups, which exceeds the safety "
            f"ceiling of {MAX_SEND_BATCH_TARGET_GROUPS}. Refusing to schedule — check the target "
            f"filters (Group/Collection/Geo) before retrying."
        )

    already_sent = _already_sent_group_names(batch_name)
    pending_groups = remaining_targets(effective_groups, already_sent)
    final_group_list = list(already_sent) + pending_groups if already_sent else effective_groups

    wave_size = doc.wave_size or settings.default_wave_size or 25
    waves_total = max(1, -(-len(final_group_list) // wave_size))
    waves_sent = -(-len(already_sent) // wave_size) if already_sent else 0

    frappe.db.set_value(SEND_BATCH_DOCTYPE, batch_name, {
        "resolved_target_groups": json.dumps(final_group_list),
        "total_groups": len(final_group_list),
        "real_target_group_count": len(real_group_names),
        "sent_in_test_mode": 1 if is_test_mode(settings) else 0,
        "waves_total": waves_total,
        "waves_sent": waves_sent,
        "status": "Scheduled",
    })
    frappe.db.commit()
    return {"total_groups": len(final_group_list), "waves_total": waves_total}


def _wave_slice(resolved_target_groups, wave_size, wave_number):
    start = (wave_number - 1) * wave_size
    end = start + wave_size
    return resolved_target_groups[start:end]


def _record_send_message(wa_group, origin, status, sent_at, message_body="", media_url=None,
                          batch=None, wave_number=None, contact_phone=None, source_turn=None,
                          auto_reply_rule=None, external_sender_phone=None, sent_in_test_mode=0,
                          glific_message_id=None, our_message_uuid=None, error=None):
    doc = frappe.new_doc(SEND_MESSAGE_DOCTYPE)
    doc.wa_group = wa_group
    doc.origin = origin
    doc.status = status
    doc.sent_at = sent_at
    doc.message_body = message_body or ""
    doc.media_url = media_url
    doc.batch = batch
    doc.wave_number = wave_number
    doc.contact_phone = contact_phone
    doc.source_turn = source_turn
    doc.auto_reply_rule = auto_reply_rule
    doc.external_sender_phone = external_sender_phone
    doc.sent_in_test_mode = sent_in_test_mode
    doc.glific_message_id = glific_message_id
    doc.our_message_uuid = our_message_uuid
    doc.error = error
    doc.insert(ignore_permissions=True)
    return doc


def _bulk_record_failed_sends(group_names, origin, sent_at, error, message_body="", media_url=None,
                               batch=None, wave_number=None, sent_in_test_mode=0):
    if not group_names:
        return
    user = frappe.session.user
    error_text = error[:500] if error else "Aborted"
    for group_name in group_names:
        frappe.db.sql(
            """
            INSERT INTO "tabWA Send Message"
                (name, wa_group, origin, status, sent_at, message_body, media_url,
                 batch, wave_number, sent_in_test_mode, error,
                 creation, modified, owner, modified_by)
            VALUES
                (%(name)s, %(wa_group)s, %(origin)s, %(status)s, %(sent_at)s, %(message_body)s, %(media_url)s,
                 %(batch)s, %(wave_number)s, %(sent_in_test_mode)s, %(error)s,
                 now(), now(), %(user)s, %(user)s)
            """,
            {
                "name": frappe.generate_hash(length=10),
                "wa_group": group_name,
                "origin": origin,
                "status": "Failed",
                "sent_at": sent_at,
                "message_body": message_body or "",
                "media_url": media_url,
                "batch": batch,
                "wave_number": wave_number,
                "sent_in_test_mode": sent_in_test_mode,
                "error": error_text,
                "user": user,
            },
        )
    frappe.db.commit()


def _resolve_poll_id_cache_entries(doc, pending):
    poll_id_cache = {}
    if doc.send_kind != "Poll":
        return poll_id_cache, None

    needed_uuids = set()
    for group_name in pending:
        uuid = _resolve_poll_uuid_for_group(doc, group_name)
        if not uuid:
            return poll_id_cache, f"No matching or default Poll UUID found for group {group_name}."
        needed_uuids.add(uuid)

    for uuid in needed_uuids:
        numeric_poll_id = get_glific_poll_id(uuid)
        if not numeric_poll_id:
            return poll_id_cache, (
                f"Could not resolve Poll UUID {uuid} to a numeric Glific Poll ID. "
                f"Run Sync Poll Labels first."
            )
        poll_id_cache[uuid] = numeric_poll_id

    return poll_id_cache, None


def _send_one_group(client, doc, group_name, poll_id_cache):
    glific_id = frappe.db.get_value("WA Group", group_name, "glific_group_id")
    if not glific_id:
        raise GlificTerminalError(f"Unknown WA Group: {group_name}")

    our_message_uuid, glific_message_id = None, None

    if doc.send_kind == "Poll":
        poll_uuid = _resolve_poll_uuid_for_group(doc, group_name)
        if not poll_uuid or poll_uuid not in poll_id_cache:
            raise GlificTerminalError(
                f"No resolved numeric Glific Poll ID available for group {group_name} "
                f"(poll_uuid={poll_uuid!r}). This should have been caught before the wave started."
            )
        result = send_poll_to_wa_group(client, glific_id, poll_id_cache[poll_uuid])
        message = result.get("message") or {}
        our_message_uuid, glific_message_id = message.get("uuid"), message.get("id")

    elif doc.send_kind == "Flow":
        start_wa_group_flow(client, glific_id, doc.glific_flow_id)

    elif doc.send_kind == "Media":
        media_id = poll_id_cache.get("_media_id")
        result = send_message_to_wa_group(
            client, glific_id, doc.message_body or "",
            media_id=media_id, msg_type=(doc.media_type or "image").upper(),
        )
        message = result.get("message") or {}
        our_message_uuid, glific_message_id = message.get("uuid"), message.get("id")

    else:
        result = send_message_to_wa_group(client, glific_id, doc.message_body or "")
        message = result.get("message") or {}
        our_message_uuid, glific_message_id = message.get("uuid"), message.get("id")

    if glific_message_id:
        glific_message_id = str(glific_message_id)
    return our_message_uuid, glific_message_id


def _claim_wave(batch_name, wave_number):
    claimed = frappe.db.sql(
        """
        UPDATE "tabWA Send Batch"
        SET status = 'Throttling', modified = now()
        WHERE name = %(name)s
          AND status IN ('Scheduled', 'Throttling')
          AND COALESCE(waves_sent, 0) < %(wave_number)s
        RETURNING name
        """,
        {"name": batch_name, "wave_number": wave_number},
    )
    frappe.db.commit()
    return bool(claimed)


def dispatch_send_wave(batch_name, wave_number):
    if not _claim_wave(batch_name, wave_number):
        return {"status": "skipped", "reason": "wave already claimed or batch not eligible"}

    try:
        return _dispatch_send_wave_inner(batch_name, wave_number)
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            title="WAGroupBot wave: unhandled exception, forcing finalize",
            message=f"{batch_name}/{wave_number}: {frappe.get_traceback()}",
        )
        try:
            doc = frappe.get_doc(SEND_BATCH_DOCTYPE, batch_name)
            settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
            pending = json.loads(doc.resolved_target_groups or "[]")
            already_done = set(_already_sent_group_names(batch_name, wave_number=wave_number))
            wave_size = doc.wave_size or settings.default_wave_size or 25
            still_pending = [g for g in _wave_slice(pending, wave_size, wave_number) if g not in already_done]
            if still_pending:
                _bulk_record_failed_sends(
                    still_pending, "Batch Wave", now_datetime(), str(e)[:500],
                    message_body=doc.message_body, media_url=doc.media_url,
                    batch=batch_name, wave_number=wave_number,
                    sent_in_test_mode=1 if is_test_mode(settings) else 0,
                )
            _finalize_wave(batch_name, doc, wave_number, settings)
        except Exception:
            frappe.log_error(
                title="WAGroupBot wave: finalize-after-crash itself failed",
                message=f"{batch_name}/{wave_number}: {frappe.get_traceback()}",
            )
        return {"status": "error", "message": str(e)}


def _dispatch_send_wave_inner(batch_name, wave_number):
    doc = frappe.get_doc(SEND_BATCH_DOCTYPE, batch_name)
    settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)

    try:
        _ensure_test_group_still_valid(settings)
    except Exception as e:
        _finalize_wave(batch_name, doc, wave_number, settings)
        frappe.log_error(title="WAGroupBot wave aborted: test group invalid",
                          message=f"{batch_name}/{wave_number}: {e}")
        return {"status": "error", "message": str(e)}

    resolved = json.loads(doc.resolved_target_groups or "[]")
    wave_size = doc.wave_size or settings.default_wave_size or 25
    wave_groups = _wave_slice(resolved, wave_size, wave_number)

    already_done = set(_already_sent_group_names(batch_name, wave_number=wave_number))
    pending = [g for g in wave_groups if g not in already_done]

    sent_in_test_mode = 1 if is_test_mode(settings) else 0

    if not pending:
        _finalize_wave(batch_name, doc, wave_number, settings)
        return {"sent": 0, "failed": 0}

    poll_id_cache, poll_error = _resolve_poll_id_cache_entries(doc, pending)
    if poll_error:
        _bulk_record_failed_sends(
            pending, "Batch Wave", now_datetime(), poll_error,
            message_body=doc.message_body, media_url=doc.media_url,
            batch=batch_name, wave_number=wave_number, sent_in_test_mode=sent_in_test_mode,
        )
        frappe.log_error(title="WAGroupBot wave aborted: poll resolution failed",
                          message=f"{batch_name}/{wave_number}: {poll_error}")
        _finalize_wave(batch_name, doc, wave_number, settings)
        return {"status": "error", "message": poll_error}

    client = GlificClient()

    if doc.send_kind == "Media":
        try:
            resolved_url = resolve_outbound_media_url(doc, settings=settings)
            media = create_message_media(
                client, resolved_url, caption=doc.message_body,
                media_type=(doc.media_type or "image").upper(),
            )
            poll_id_cache["_media_url"] = resolved_url
            poll_id_cache["_media_id"] = media.get("id")
        except GlificManualTokenError as e:
            _bulk_record_failed_sends(
                pending, "Batch Wave", now_datetime(), str(e),
                message_body=doc.message_body, media_url=doc.media_url,
                batch=batch_name, wave_number=wave_number, sent_in_test_mode=sent_in_test_mode,
            )
            frappe.log_error(title="WAGroupBot wave aborted: token expired (media upload)",
                              message=f"{batch_name}/{wave_number}: {e}")
            _finalize_wave(batch_name, doc, wave_number, settings)
            return {"status": "error", "message": str(e)}
        except Exception as e:
            _bulk_record_failed_sends(
                pending, "Batch Wave", now_datetime(), str(e),
                message_body=doc.message_body, media_url=doc.media_url,
                batch=batch_name, wave_number=wave_number, sent_in_test_mode=sent_in_test_mode,
            )
            frappe.log_error(title="WAGroupBot wave aborted: media creation failed",
                              message=f"{batch_name}/{wave_number}: {e}")
            _finalize_wave(batch_name, doc, wave_number, settings)
            return {"status": "error", "message": str(e)}

    sent, failed, skipped_in_flight = 0, 0, 0
    for i, group_name in enumerate(pending):
        if i > 0:
            time.sleep(SEND_PACING_SECONDS)

        intent_key = _send_intent_key(batch_name, wave_number, group_name)
        if not acquire_lock(intent_key, timeout=SEND_INTENT_LOCK_SECONDS):
            skipped_in_flight += 1
            continue

        try:
            our_message_uuid, glific_message_id = _send_one_group(client, doc, group_name, poll_id_cache)
            _record_send_message(
                group_name, "Batch Wave", "Sent", now_datetime(),
                message_body=doc.message_body, media_url=doc.media_url,
                batch=batch_name, wave_number=wave_number,
                sent_in_test_mode=sent_in_test_mode,
                glific_message_id=glific_message_id, our_message_uuid=our_message_uuid,
            )
            sent += 1
            frappe.db.commit()
        except GlificManualTokenError as e:
            release_lock(intent_key)
            remaining = pending[i:]
            _bulk_record_failed_sends(
                remaining, "Batch Wave", now_datetime(), str(e),
                message_body=doc.message_body, media_url=doc.media_url,
                batch=batch_name, wave_number=wave_number, sent_in_test_mode=sent_in_test_mode,
            )
            failed += len(remaining)
            frappe.log_error(title="WAGroupBot wave aborted: token expired",
                              message=f"{batch_name}/{wave_number} stopped at group={group_name}: {e}")
            break
        except Exception as e:
            _record_send_message(
                group_name, "Batch Wave", "Failed", now_datetime(),
                message_body=doc.message_body, media_url=doc.media_url,
                batch=batch_name, wave_number=wave_number,
                sent_in_test_mode=sent_in_test_mode, error=str(e)[:500],
            )
            frappe.log_error(title="WAGroupBot wave send failed", message=f"{batch_name}/{wave_number} group={group_name}: {e}")
            failed += 1
            frappe.db.commit()
        finally:
            release_lock(intent_key)

    if skipped_in_flight:
        frappe.log_error(
            title="WAGroupBot wave: groups skipped as already in flight",
            message=f"{batch_name}/{wave_number}: {skipped_in_flight} group(s) skipped to avoid a duplicate send.",
        )

    _finalize_wave(batch_name, doc, wave_number, settings)
    return {"sent": sent, "failed": failed, "skipped_in_flight": skipped_in_flight}


def _delete_batch_media_file(batch_name, file_url):
    try:
        file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
        if file_name:
            frappe.delete_doc("File", file_name, ignore_permissions=True, force=True)
            frappe.db.set_value(SEND_BATCH_DOCTYPE, batch_name, "media_file", None)
            frappe.db.commit()
    except Exception:
        frappe.log_error(
            title="WAGroupBot: failed to delete batch media file after terminal status",
            message=f"{batch_name}: {frappe.get_traceback()}",
        )


def _finalize_wave(batch_name, doc, wave_number, settings):
    resolved = json.loads(doc.resolved_target_groups or "[]")
    wave_size = doc.wave_size or settings.default_wave_size or 25
    waves_total = max(1, -(-len(resolved) // wave_size))
    is_last_wave = wave_number >= waves_total

    total_failed = frappe.db.count(SEND_MESSAGE_DOCTYPE, {
        "batch": batch_name, "origin": "Batch Wave", "status": "Failed",
    })
    total_sent = frappe.db.count(SEND_MESSAGE_DOCTYPE, {
        "batch": batch_name, "origin": "Batch Wave", "status": "Sent",
    })

    updates = {"waves_sent": wave_number}
    if is_last_wave:
        if total_failed and not total_sent:
            updates["status"] = "Failed"
        elif total_failed:
            updates["status"] = "Partially Failed"
        else:
            updates["status"] = "Sent"
        updates["next_wave_at"] = None
    else:
        updates["status"] = "Scheduled"
        wave_gap_minutes = doc.wave_gap_minutes if doc.wave_gap_minutes is not None else (settings.default_wave_gap_minutes or 10)
        updates["next_wave_at"] = add_to_date(now_datetime(), minutes=wave_gap_minutes)

    frappe.db.set_value(SEND_BATCH_DOCTYPE, batch_name, updates)
    frappe.db.commit()

    if is_last_wave and doc.send_kind == "Media" and doc.media_file:
        _delete_batch_media_file(doc.name, doc.media_file)


def run_due_send_waves():
    frappe.only_for("System Manager")
    due = frappe.get_all(
        SEND_BATCH_DOCTYPE,
        filters={"status": "Scheduled"},
        or_filters=[
            {"scheduled_send_at": ["<=", now_datetime()]},
            {"next_wave_at": ["<=", now_datetime()]},
        ],
        fields=["name", "waves_sent"],
    )

    dispatched = 0
    for row in due:
        next_wave_number = (row.waves_sent or 0) + 1
        _wag_enqueue(
            "tap_lms.wagroupbot.outbound.dispatch_send_wave",
            SEND_QUEUE, batch_name=row.name, wave_number=next_wave_number,
        )
        dispatched += 1
    return {"dispatched": dispatched}


def cancel_send_batch(batch_name):
    doc = frappe.get_doc(SEND_BATCH_DOCTYPE, batch_name)
    if doc.status not in ("Draft", "Scheduled", "Throttling"):
        frappe.throw("Only a Draft, Scheduled or Throttling batch can be cancelled.")
    doc.status = "Cancelled"
    doc.cancelled_at = now_datetime()
    doc.save(ignore_permissions=True)
    return doc


def _format_phone_tag(raw_phone):
    if not raw_phone:
        return None
    digits = "".join(ch for ch in str(raw_phone) if ch.isdigit())
    if len(digits) < 10:
        return None
    return f"@{digits}"


def build_tagged_reply(contact_phone, reply_text, settings=None):
    settings = settings or frappe.get_cached_doc(SETTINGS_DOCTYPE)
    reply_text = (reply_text or "").strip()

    if not settings.reply_tagging_enabled:
        return reply_text.replace(TAG_PLACEHOLDER, "").strip()

    tag = _format_phone_tag(contact_phone)
    if TAG_PLACEHOLDER in reply_text and tag:
        reply_text = reply_text.replace(TAG_PLACEHOLDER, tag, 1)
    return reply_text.replace(TAG_PLACEHOLDER, "").strip()


def _claim_turn_for_sending(turn_name):
    claimed = frappe.db.sql(
        """
        UPDATE "tabWA Group Turn"
        SET turn_status = 'Sending', modified = now()
        WHERE name = %(name)s
          AND turn_status IN ('Open', 'Drafted', 'Ready To Go', 'Failed')
        RETURNING name
        """,
        {"name": turn_name},
    )
    frappe.db.commit()
    return bool(claimed)


def send_manual_reply(turn_name, reply_text, sent_by_user=None, already_claimed=False):
    if not already_claimed and not _claim_turn_for_sending(turn_name):
        frappe.throw(
            "This conversation is already being sent or is no longer in a sendable state "
            "(it may have just been sent by the scheduled send sweep). Refresh and try again."
        )

    try:
        turn = frappe.get_doc(TURN_DOCTYPE, turn_name)
        settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
        _ensure_test_group_still_valid(settings)
        effective_group = get_effective_group(turn.wa_group, settings)

        group_id = frappe.db.get_value("WA Group", effective_group, "glific_group_id")
        if not group_id:
            frappe.throw("This turn's target WA Group has no Glific group ID — cannot send.")

        tagged_body = build_tagged_reply(turn.contact_phone, reply_text, settings)
        if not tagged_body:
            frappe.throw("Reply text cannot be empty.")

        client = GlificClient()
        try:
            result = send_message_to_wa_group(client, group_id, tagged_body)
        except GlificManualTokenError as e:
            frappe.throw(f"Glific token expired: {e}")
        except GlificTerminalError as e:
            frappe.throw(f"Glific rejected the send: {e}")

        message = result.get("message") or {}
        our_message_uuid = message.get("uuid")
        glific_message_id = str(message.get("id")) if message.get("id") else None

        sent_at = now_datetime()
        _record_send_message(
            turn.wa_group, "Direct Reply", "Sent", sent_at,
            message_body=tagged_body, contact_phone=turn.contact_phone, source_turn=turn.name,
            sent_in_test_mode=1 if is_test_mode(settings) else 0,
            glific_message_id=glific_message_id, our_message_uuid=our_message_uuid,
        )

        frappe.db.set_value(TURN_DOCTYPE, turn.name, {"is_closed": 1, "turn_status": "Sent"})

        from tap_lms.wagroupbot.inbound import _bump_rollup
        _bump_rollup(turn.wa_group, sent_at, "tagged_reply_count")

        frappe.db.commit()
        return {"status": "sent", "sent_to_wa_group": effective_group}

    except Exception:
        frappe.db.rollback()
        frappe.db.set_value(TURN_DOCTYPE, turn_name, "turn_status", "Failed")
        frappe.db.commit()
        raise


def _normalize(text):
    return (text or "").strip().lower()


def _rule_matches(rule, body):
    normalized = _normalize(body)
    keywords = (rule.trigger_keywords or "").strip()
    if not keywords:
        return False

    if rule.match_mode == "Exact Word":
        return normalized == keywords.lower()
    if rule.match_mode == "Starts With":
        return normalized.startswith(keywords.lower())
    if rule.match_mode == "Contains Phrase":
        pattern = r"\b" + re.escape(keywords.lower()) + r"\b"
        return bool(re.search(pattern, normalized))
    if rule.match_mode == "Any Of":
        for kw in keywords.split(","):
            kw = kw.strip().lower()
            if kw and re.search(r"\b" + re.escape(kw) + r"\b", normalized):
                return True
        return False
    if rule.match_mode == "Regex":
        try:
            return bool(re.search(keywords, body or "", re.IGNORECASE))
        except re.error:
            return False
    return False


def _recent_reply_exists(wa_group, contact_phone, since_seconds=RECENT_REPLY_COOLDOWN_SECONDS):
    since = add_to_date(now_datetime(), seconds=-since_seconds)
    return bool(frappe.db.exists(SEND_MESSAGE_DOCTYPE, {
        "origin": "Direct Reply", "wa_group": wa_group, "contact_phone": contact_phone,
        "sent_at": [">=", since],
    }))


def _cooldown_active(rule, wa_group, contact_phone):
    if _recent_reply_exists(wa_group, contact_phone):
        return True
    if not rule.cooldown_minutes:
        return False
    since = add_to_date(now_datetime(), minutes=-rule.cooldown_minutes)
    return bool(frappe.db.exists(SEND_MESSAGE_DOCTYPE, {
        "origin": "Auto Reply Rule", "auto_reply_rule": rule.name,
        "wa_group": wa_group, "contact_phone": contact_phone, "sent_at": [">=", since],
    }))


def _get_active_rules():
    cached = frappe.cache().get_value(AUTO_REPLY_RULES_CACHE_KEY)
    if cached is not None:
        return cached
    rules = frappe.get_all(
        "WA Auto Reply Rule",
        filters={"is_active": 1},
        fields=["name", "match_mode", "trigger_keywords", "event_type", "wa_group",
                 "applies_to_all", "priority", "cooldown_minutes",
                 "response_type", "response_body", "response_flow_id",
                 "response_media_url", "response_media_file", "response_media_type"],
        order_by="priority desc",
    )
    frappe.cache().set_value(AUTO_REPLY_RULES_CACHE_KEY, rules, expires_in_sec=AUTO_REPLY_RULES_CACHE_TTL)
    return rules


def invalidate_auto_reply_rules_cache():
    frappe.cache().delete_value(AUTO_REPLY_RULES_CACHE_KEY)


def match_auto_reply_rule(wa_group, item_type, body, contact_phone, ai_enabled):
    rules = _get_active_rules()

    for rule in rules:
        if ai_enabled and item_type in AI_DRAFTABLE_ITEM_TYPES and rule.priority <= 0:
            continue
        if not rule.applies_to_all and rule.wa_group and rule.wa_group != wa_group:
            continue
        if rule.event_type and rule.event_type != item_type:
            continue
        if not _rule_matches(rule, body):
            continue
        if _cooldown_active(rule, wa_group, contact_phone):
            continue
        return rule
    return None


def _claim_auto_reply_dispatch(wa_group, contact_phone, rule_name, response_body):
    since = add_to_date(now_datetime(), seconds=-AUTO_REPLY_DISPATCH_GUARD_SECONDS)
    duplicate = frappe.db.exists(SEND_MESSAGE_DOCTYPE, {
        "origin": "Auto Reply Rule",
        "auto_reply_rule": rule_name,
        "wa_group": wa_group,
        "contact_phone": contact_phone,
        "message_body": response_body or "",
        "sent_at": [">=", since],
    })
    return not duplicate


def send_auto_reply(wa_group, contact_phone, rule_name):
    rule = frappe.get_doc("WA Auto Reply Rule", rule_name)
    settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)

    if not _claim_auto_reply_dispatch(wa_group, contact_phone, rule_name, rule.response_body):
        frappe.logger("wagroupbot_outbound").info(
            f"Skipping likely-duplicate auto-reply dispatch: rule={rule_name} wa_group={wa_group} contact={contact_phone}"
        )
        return

    intent_key = f"auto_reply_intent:{rule_name}:{wa_group}:{contact_phone}"
    if not acquire_lock(intent_key, timeout=AUTO_REPLY_DISPATCH_GUARD_SECONDS):
        return

    try:
        _ensure_test_group_still_valid(settings)
        effective_group = get_effective_group(wa_group, settings)

        group_id = frappe.db.get_value("WA Group", effective_group, "glific_group_id")
        if not group_id:
            return

        client = GlificClient()
        reply_text = None
        our_message_uuid, glific_message_id = None, None
        media_url_for_record = None

        if rule.response_type == "Flow" and rule.response_flow_id:
            start_wa_group_flow(client, group_id, rule.response_flow_id)
        elif rule.response_type == "Media" and (rule.response_media_file or rule.response_media_url):
            resolved_url = resolve_outbound_media_url(rule, settings=settings)
            media_url_for_record = resolved_url
            media = create_message_media(
                client, resolved_url, caption=rule.response_body,
                media_type=(rule.response_media_type or "image").upper(),
            )
            result = send_message_to_wa_group(
                client, group_id, rule.response_body or "",
                media_id=media.get("id"), msg_type=(rule.response_media_type or "image").upper(),
            )
            message = result.get("message") or {}
            our_message_uuid, glific_message_id = message.get("uuid"), message.get("id")
            reply_text = rule.response_body
        else:
            result = send_message_to_wa_group(client, group_id, rule.response_body or "")
            message = result.get("message") or {}
            our_message_uuid, glific_message_id = message.get("uuid"), message.get("id")
            reply_text = rule.response_body

        if glific_message_id:
            glific_message_id = str(glific_message_id)

        if reply_text:
            sent_at = now_datetime()
            _record_send_message(
                wa_group, "Auto Reply Rule", "Sent", sent_at,
                message_body=reply_text, media_url=media_url_for_record,
                contact_phone=contact_phone, auto_reply_rule=rule.name,
                sent_in_test_mode=1 if is_test_mode(settings) else 0,
                glific_message_id=glific_message_id, our_message_uuid=our_message_uuid,
            )

            from tap_lms.wagroupbot.inbound import _bump_rollup
            _bump_rollup(wa_group, sent_at, "tagged_reply_count")

            frappe.db.commit()
    except GlificManualTokenError as e:
        frappe.log_error(title="WAGroupBot auto-reply blocked: token expired", message=f"{rule_name}: {e}")
    except Exception as e:
        frappe.log_error(title="WAGroupBot auto-reply failed", message=f"{rule_name}: {e}")
    finally:
        release_lock(intent_key)


def _claim_ready_turns(limit):
    rows = frappe.db.sql(
        """
        UPDATE "tabWA Group Turn"
        SET turn_status = 'Sending', modified = now()
        WHERE name IN (
            SELECT name FROM "tabWA Group Turn"
            WHERE turn_status = 'Ready To Go'
              AND (scheduled_send_after IS NULL OR scheduled_send_after <= %(now)s)
            ORDER BY ai_urgency DESC, last_item_at ASC
            LIMIT %(limit)s
            FOR UPDATE SKIP LOCKED
        )
        RETURNING name, wa_group, ai_reply, ai_urgency
        """,
        {"now": now_datetime(), "limit": limit},
        as_dict=True,
    )
    frappe.db.commit()
    return rows


def send_ready_turns():
    due = _claim_ready_turns(SEND_SWEEP_BATCH_SIZE)
    if not due:
        return {"sent": 0, "failed": 0}

    sent, failed = 0, 0
    for i, row in enumerate(due):
        if i > 0:
            time.sleep(SEND_PACING_SECONDS)
        try:
            send_manual_reply(row.name, row.ai_reply, sent_by_user=None, already_claimed=True)
            sent += 1
        except Exception as e:
            failed += 1
            frappe.db.set_value(TURN_DOCTYPE, row.name, "turn_status", "Discarded")
            frappe.log_error(title="WAGroupBot ready-turn send failed", message=f"{row.name}: {e}")
        frappe.db.commit()

    frappe.db.set_value(SETTINGS_DOCTYPE, None, {
        "last_send_sweep_status": "Failed" if failed and not sent else "Success",
        "last_send_sweep_message": f"Sent {sent}, failed {failed}",
        "last_send_sweep_at": now_datetime(),
    })
    frappe.db.commit()

    return {"sent": sent, "failed": failed}