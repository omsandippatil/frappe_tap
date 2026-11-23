import re
import unicodedata
from collections import defaultdict

import frappe
from frappe.utils import now_datetime, add_to_date

from tap_lms.wagroupbot.glific import to_datetime, normalize_phone
from tap_lms.wagroupbot.redis_lock import acquire_lock, release_lock, refresh_lock
from tap_lms.tap_lms.doctype.wa_bot_settings.wa_bot_settings import is_ignored_staff_number, get_my_tag_id

SETTINGS_DOCTYPE = "WA Bot Settings"
TURN_DOCTYPE = "WA Group Turn"
TURN_ITEM_DOCTYPE = "WA Group Turn Item"
REACTION_DOCTYPE = "WA Group Reaction"
REACTION_RETRY_QUEUE_DOCTYPE = "WA Reaction Retry Queue"
SEND_MESSAGE_DOCTYPE = "WA Send Message"
ROLLUP_DOCTYPE = "WA Event Rollup"
DEFAULT_POLL_INTERVAL_MINUTES = 60
DEFAULT_MAX_TURN_ITEMS = 40
CLOSE_GRACE_SECONDS = 5
DEFAULT_BQ_MAX_BYTES_BILLED = 1073741824
DEFAULT_POLL_ATTRIBUTION_WINDOW_HOURS = 48
SEND_ECHO_RECONCILE_LOOKBACK_MINUTES = 180
MAX_BQ_RECONCILE_ATTEMPTS = 5
MAX_REACTION_RETRY_ATTEMPTS = 10
LOCK_HEARTBEAT_TIMEOUT_SECONDS = 180

# Checkpoint writes during a long ingest chunk loop are now time-based, not
# row-count-based (previously: every `ingest_chunk_size` rows, which could
# mean 4-5 writes to the WA Bot Settings singleton for one pull). A fast
# pull of a few thousand rows that finishes in a couple of seconds no longer
# checkpoints repeatedly for no reason; a slow pull still checkpoints often
# enough that a crash loses at most this many seconds of progress.
CHECKPOINT_INTERVAL_SECONDS = 30

# --- Self-triggered housekeeping (no scheduler/hooks.py entry required) ---
# pull_messages() is already invoked regularly: a human clicking "Pull
# Latest", and automatically every ~10 minutes by the dashboard's own
# client-side auto_pull_if_due() timer (see wa_groups.js start_auto_pull).
# Riding on that existing, already-frequent call lets housekeeping run
# without any cron/scheduler_events entry. It is throttled independently so
# it does not actually do the purge work on every single pull — only once
# the throttle window has elapsed.
HOUSEKEEPING_CACHE_KEY = "wagroupbot:last_housekeeping_at"
HOUSEKEEPING_INTERVAL_SECONDS = 6 * 60 * 60  # run purges at most every 6 hours

ATTRIBUTABLE_EVENT_TYPES = {"Poll Response", "Text", "Media", "Voice"}

BQ_MESSAGE_COLUMNS = (
    "id, uuid, body, type, flow, status, bsp_status, contact_phone, "
    "contact_name, media_url, gcs_url, message_broadcast_id, wa_group_id, "
    "wa_group_name, flow_label, poll_content, wa_phone_id, inserted_at, is_dm"
)

BQ_GCS_BACKFILL_COLUMNS = "id, gcs_url, type, inserted_at, updated_at"

COUNTER_BY_TYPE = {
    "Text": "text_count",
    "Media": "media_count",
    "Voice": "voice_count",
    "Poll Response": "poll_response_count",
    "Reaction": "reaction_count",
    "Sticker": "sticker_count",
}

TURN_ITEM_TYPES = {
    "text": "Text", "image": "Media", "video": "Media", "document": "Media",
    "audio": "Voice", "ptt": "Voice", "sticker": "Sticker",
}

VISUAL_MIME_TYPES = {"image", "sticker"}
RECORDABLE_MEDIA_MIME_TYPES = VISUAL_MIME_TYPES | {"video"}
GCS_BACKFILL_MIME_TYPES = ("image", "video", "sticker")

TAG_EXTRACT_PATTERN = re.compile(r"^@(\d{6,20})\b")

EMPTY_POLL_CONTENT_VALUES = ("", "{}")

VARIATION_SELECTOR_PATTERN = re.compile(
    "[\U0000FE00-\U0000FE0F\U000E0100-\U000E01EF]"
)
SKIN_TONE_MODIFIER_PATTERN = re.compile("[\U0001F3FB-\U0001F3FF]")
ZERO_WIDTH_JOINER = "\u200D"


def _enqueue_on_ingest_queue(method, **kwargs):
    from tap_lms.wagroupbot.queues import enqueue, INGEST_QUEUE
    return enqueue(method, INGEST_QUEUE, **kwargs)


def _set_settings_values(values):
    try:
        frappe.db.set_single_value(SETTINGS_DOCTYPE, values)
    except Exception:
        frappe.log_error(
            title="WAGroupBot settings update failed",
            message=f"values={values}: {frappe.get_traceback()}",
        )


def normalize_emoji(raw_emoji):
    if not raw_emoji:
        return None
    text = unicodedata.normalize("NFC", str(raw_emoji).strip())
    if not text:
        return None
    text = VARIATION_SELECTOR_PATTERN.sub("", text)
    text = SKIN_TONE_MODIFIER_PATTERN.sub("", text)
    text = text.replace(ZERO_WIDTH_JOINER, "")
    text = text.strip()
    return text or None


def classify_event_type(row, poll_choice=None, has_poll_vote=False):
    """Classify one BigQuery message row into a turn-item type.

    IMPORTANT: when a row genuinely carries poll content (has_real_poll_content)
    but we could not match the sender to any voter in that content (poll_choice
    and has_poll_vote both falsy — e.g. the voter-phone match in
    _extract_poll_choice failed), this MUST resolve to "System" (skipped),
    never fall through to the generic text/media mapping. Falling through
    used to classify the row as plain Text with the raw poll_content JSON
    blob as its body, which could reach AI drafting and auto-reply matching
    as garbage input. If a poll vote failed to resolve, we drop that one row
    rather than risk a bogus reply being generated or sent from it.
    """
    item_type = (row.get("type") or "").lower()
    mapped = TURN_ITEM_TYPES.get(item_type)
    poll_content = (row.get("poll_content") or "").strip()
    has_real_poll_content = poll_content not in EMPTY_POLL_CONTENT_VALUES

    if has_real_poll_content:
        if row.get("flow") == "outbound":
            return "Poll Sent"
        if item_type in ("image", "video", "document", "sticker"):
            # A media message that happens to carry poll_content metadata
            # (not itself a vote) — classify by its real media type.
            return mapped or "System"
        if poll_choice or has_poll_vote:
            return "Poll Response"
        # Poll content present, inbound, not media, but no voter match:
        # do not let this become a stray Text item.
        return "System"

    return mapped or "System"


def extract_media_mime_type(row):
    item_type = (row.get("type") or "").lower()
    if item_type == "sticker":
        return "sticker"
    if item_type in ("image", "video", "audio", "ptt", "document"):
        return "audio" if item_type == "ptt" else item_type
    return None


def extract_tagged_user_id(body):
    if not body:
        return None
    match = TAG_EXTRACT_PATTERN.match(body.strip())
    return match.group(1) if match else None


def _clean_gcs_url(value):
    if not value:
        return None
    text = str(value).strip()
    if not text or text.lower() == "null":
        return None
    return text


def _poll_question_text(poll_content):
    """Extracts the human-readable poll question from a BigQuery row's
    poll_content JSON (e.g. {"options":[...],"text":"Sonia test poll 1"}).

    Outbound poll-send rows carry the question here, not in `body` — body
    is empty for a poll send. Used as the fallback for WA Send Message's
    message_body when recording an externally-discovered poll send, so
    poll broadcasts don't show up with a blank body in send history.
    """
    data = _safe_load_json(poll_content)
    if not isinstance(data, dict):
        return None
    text = data.get("text")
    return str(text).strip()[:500] if text else None


def _extract_poll_choice(poll_content, contact_phone):
    if not poll_content or not contact_phone:
        return None, False
    data = _safe_load_json(poll_content)
    if data is None:
        frappe.logger("wagroupbot_inbound").warning(
            f"poll_content failed to parse as JSON for contact {contact_phone}"
        )
        return None, False
    if not isinstance(data, dict):
        return None, False

    options = data.get("options")
    if not isinstance(options, list):
        return None, False

    picked = []
    any_voter_match = False
    for opt in options:
        if not isinstance(opt, dict):
            continue
        if _voter_matches(opt.get("voters"), contact_phone):
            any_voter_match = True
            picked.append(opt.get("name"))

    if picked:
        return ", ".join(str(p) for p in picked if p)[:140], True

    if not any_voter_match:
        frappe.logger("wagroupbot_inbound").warning(
            f"has_real_poll_content but no voter match for contact {contact_phone}"
        )
    return None, False


def _safe_load_json(value):
    import json
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _voter_matches(voters, phone):
    if not isinstance(voters, list):
        return False
    target = normalize_phone(phone)
    for voter in voters:
        voter_phone = voter.get("phone") if isinstance(voter, dict) else voter
        if not voter_phone:
            continue
        candidate = str(voter_phone).split("@")[0].strip()
        normalized_candidate = normalize_phone(candidate)
        if normalized_candidate == target:
            return True
    return False


def _poll_lock_remaining_minutes(settings):
    last_attempt = to_datetime(settings.last_poll_at)
    if not last_attempt:
        return 0
    interval = settings.manual_pull_min_interval_minutes or DEFAULT_POLL_INTERVAL_MINUTES
    elapsed_seconds = frappe.utils.time_diff_in_seconds(now_datetime(), last_attempt.replace(tzinfo=None))
    return max(0, interval - (elapsed_seconds / 60))


def _resolve_checkpoint(raw_value, default_lookback_days=None, default_lookback_hours=None):
    parsed = frappe.utils.get_datetime(raw_value) if raw_value else None
    if parsed and parsed.year > 1:
        return parsed
    if default_lookback_days:
        return add_to_date(now_datetime(), days=-default_lookback_days)
    return add_to_date(now_datetime(), hours=-(default_lookback_hours or 24))


def pull_messages():
    settings = frappe.get_single(SETTINGS_DOCTYPE)
    if not settings.bq_dataset or not settings.bq_table or not settings.bq_project:
        _set_settings_values({
            "last_poll_status": "Failed",
            "last_poll_message": "BigQuery is not fully configured.",
        })
        frappe.db.commit()
        return {"status": "error", "message": "BigQuery is not fully configured."}

    remaining = _poll_lock_remaining_minutes(settings)
    if remaining > 0:
        message = f"Pull skipped: next pull available in {int(remaining)} min (cooldown lock)."
        _set_settings_values({
            "last_poll_status": "Skipped",
            "last_poll_message": message,
        })
        frappe.db.commit()
        return {"status": "skipped", "message": message}

    if not acquire_lock("pull_messages", timeout=LOCK_HEARTBEAT_TIMEOUT_SECONDS):
        return {"status": "skipped", "message": "A pull is already running."}

    # Refresh immediately after acquiring: the lock was just set with a
    # LOCK_HEARTBEAT_TIMEOUT_SECONDS TTL, and the first refresh otherwise
    # only happens at the first ingest-chunk boundary (every
    # ingest_chunk_size rows). If fetching the first BigQuery page itself
    # takes longer than the TTL (slow query, BQ throttling), the lock can
    # expire before a single row is processed, letting a second pull start
    # concurrently. This call is a no-op cost-wise and closes that window.
    refresh_lock("pull_messages", timeout=LOCK_HEARTBEAT_TIMEOUT_SECONDS)

    try:
        _set_settings_values({
            "last_poll_at": now_datetime(),
            "last_poll_status": "Failed",
            "last_poll_message": "Pull in progress...",
        })
        frappe.db.commit()

        try:
            close_expired_turns(settings)

            lookback = settings.fetch_lookback_minutes or 15
            row_limit = settings.fetch_row_limit or 2000
            max_lookback_days = settings.fetch_max_lookback_days or 35
            max_lookback = add_to_date(now_datetime(), days=-max_lookback_days)

            checkpoint = _resolve_checkpoint(settings.bq_checkpoint_datetime, default_lookback_hours=24)
            query_since = add_to_date(checkpoint, minutes=-lookback)
            if query_since < max_lookback:
                frappe.log_error(title="WAGroupBot checkpoint clamped",
                                  message=f"query_since {query_since} older than {max_lookback_days}d, clamping")
                query_since = max_lookback

            refresh_lock("pull_messages", timeout=LOCK_HEARTBEAT_TIMEOUT_SECONDS)

            try:
                msg_rows = _query_bq_messages(settings, since=query_since, limit=row_limit)
                refresh_lock("pull_messages", timeout=LOCK_HEARTBEAT_TIMEOUT_SECONDS)
                msg_result = _ingest_message_rows(msg_rows, checkpoint, row_limit, settings)
            except Exception as e:
                frappe.db.rollback()
                frappe.log_error(title="WAGroupBot message pull failed", message=frappe.get_traceback())
                _set_settings_values({
                    "last_poll_status": "Failed", "last_poll_message": str(e)[:500],
                })
                frappe.db.commit()
                return {"status": "error", "message": str(e)}

            try:
                reaction_checkpoint = _resolve_checkpoint(
                    settings.bq_reaction_checkpoint_datetime, default_lookback_days=max_lookback_days,
                )
                reaction_since = add_to_date(reaction_checkpoint, minutes=-lookback)
                if reaction_since < max_lookback:
                    reaction_since = max_lookback
                reaction_rows = _query_bq_reactions(settings, since=reaction_since, limit=row_limit)
                reaction_result = _ingest_reaction_rows(reaction_rows, reaction_checkpoint, until=now_datetime(), settings=settings)
            except Exception as e:
                frappe.db.rollback()
                frappe.log_error(title="WAGroupBot reaction pull failed", message=frappe.get_traceback())
                reaction_result = {"status": "error", "message": str(e)}

            try:
                gcs_checkpoint = _resolve_checkpoint(settings.bq_gcs_backfill_checkpoint_datetime, default_lookback_hours=24)
                gcs_since = add_to_date(gcs_checkpoint, minutes=-lookback)
                if gcs_since < max_lookback:
                    gcs_since = max_lookback
                gcs_rows = _query_bq_gcs_backfill(settings, since=gcs_since, limit=row_limit)
                gcs_result = _ingest_gcs_backfill_rows(gcs_rows, gcs_checkpoint)
            except Exception as e:
                frappe.db.rollback()
                frappe.log_error(title="WAGroupBot GCS backfill failed", message=str(e))
                gcs_result = {"status": "error", "message": str(e)}

            try:
                mark_unreconciled_sends_for_retry()
            except Exception as e:
                frappe.log_error(title="WAGroupBot reconcile-retry pass failed", message=str(e))

            # Self-triggered housekeeping: runs at most once every
            # HOUSEKEEPING_INTERVAL_SECONDS, piggybacking on this already-
            # frequent call. No scheduler_events entry required. Failures
            # here never fail the pull itself.
            try:
                housekeeping_result = _maybe_run_housekeeping()
            except Exception as e:
                frappe.log_error(title="WAGroupBot housekeeping failed", message=str(e))
                housekeeping_result = {"status": "error", "message": str(e)}

            refresh_lock("pull_messages", timeout=LOCK_HEARTBEAT_TIMEOUT_SECONDS)

            summary = (
                f"Messages: inserted={msg_result.get('inserted', 0)}, "
                f"skipped={msg_result.get('skipped', 0)}, "
                f"ignored_staff={msg_result.get('ignored_staff', 0)}, "
                f"unresolved_group={msg_result.get('unresolved_group', 0)}, "
                f"outbound_reconciled={msg_result.get('outbound_reconciled', 0)}, "
                f"outbound_external_recorded={msg_result.get('outbound_external_recorded', 0)}, "
                f"truncated={msg_result.get('truncated', False)}. "
                f"Reactions: {reaction_result}. "
                f"GCS backfill: {gcs_result}. "
                f"Housekeeping: {housekeeping_result}"
            )
            _set_settings_values({
                "last_poll_status": "Success", "last_poll_message": summary,
            })
            frappe.db.commit()
            return {
                "status": "success", "messages": msg_result, "reactions": reaction_result,
                "gcs_backfill": gcs_result, "housekeeping": housekeeping_result,
            }

        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(title="WAGroupBot pull crashed", message=frappe.get_traceback())
            _set_settings_values({
                "last_poll_status": "Failed",
                "last_poll_message": f"Pull crashed: {str(e)[:450]}",
            })
            frappe.db.commit()
            return {"status": "error", "message": str(e)}
    finally:
        release_lock("pull_messages")


def _maybe_run_housekeeping():
    """Runs the periodic cleanup jobs that would normally live in
    hooks.py's scheduler_events, without needing any scheduler config.

    Throttled via a Redis-backed timestamp so it only actually executes
    its work once every HOUSEKEEPING_INTERVAL_SECONDS, however often
    pull_messages() itself is called (manually or via the dashboard's
    auto_pull_if_due timer). Safe to call on every pull — on a cache miss
    or any error reading the cache, it proceeds (fails open on the "should
    I run" check) rather than silently never running housekeeping.
    """
    cache = frappe.cache()
    try:
        last_run_raw = cache.get_value(HOUSEKEEPING_CACHE_KEY)
    except Exception:
        last_run_raw = None

    now = now_datetime()
    if last_run_raw:
        try:
            last_run = frappe.utils.get_datetime(last_run_raw)
            elapsed = frappe.utils.time_diff_in_seconds(now, last_run)
            if elapsed < HOUSEKEEPING_INTERVAL_SECONDS:
                return {"status": "skipped", "next_run_in_seconds": int(HOUSEKEEPING_INTERVAL_SECONDS - elapsed)}
        except Exception:
            pass  # malformed cache value — fall through and run

    results = {}

    try:
        from tap_lms.tap_lms.doctype.wa_media_token.wa_media_token import purge_expired
        purge_expired()
        results["media_tokens_purged"] = "ok"
    except Exception as e:
        results["media_tokens_purged"] = f"error: {e}"
        frappe.log_error(title="WAGroupBot housekeeping: media token purge failed", message=str(e))

    try:
        from tap_lms.tap_lms.doctype.wa_reaction_retry_queue.wa_reaction_retry_queue import purge_exhausted
        purge_exhausted()
        results["reaction_retry_queue_purged"] = "ok"
    except Exception as e:
        results["reaction_retry_queue_purged"] = f"error: {e}"
        frappe.log_error(title="WAGroupBot housekeeping: reaction retry purge failed", message=str(e))

    try:
        cache.set_value(HOUSEKEEPING_CACHE_KEY, now.isoformat(), expires_in_sec=HOUSEKEEPING_INTERVAL_SECONDS * 4)
    except Exception:
        frappe.log_error(title="WAGroupBot housekeeping: failed to update throttle timestamp", message="")

    results["status"] = "ran"
    results["ran_at"] = now.isoformat()
    return results


def _bq_max_bytes_billed(settings):
    return int(settings.bq_max_bytes_billed or DEFAULT_BQ_MAX_BYTES_BILLED)


def _query_bq_messages(settings, since, until=None, wa_group_glific_id=None, limit=2000):
    from tap_lms.wagroupbot.bq import run_query

    conditions = [
        "wa_group_id IS NOT NULL",
        "(is_dm = FALSE OR is_dm IS NULL)",
        "inserted_at > @since",
    ]
    params = {"since": since}
    if until:
        conditions.append("inserted_at <= @until")
        params["until"] = until
    if wa_group_glific_id:
        conditions.append("wa_group_id = @wa_group_id")
        params["wa_group_id"] = wa_group_glific_id

    sql = f"""
        SELECT {BQ_MESSAGE_COLUMNS}
        FROM `{settings.bq_project}.{settings.bq_dataset}.{settings.bq_table}`
        WHERE {" AND ".join(conditions)}
        ORDER BY inserted_at ASC
        LIMIT {int(limit)}
    """
    return run_query(sql, params=params, max_bytes_billed=_bq_max_bytes_billed(settings))


def _query_bq_messages_by_ids(settings, wa_message_ids):
    """Batched replacement for _query_bq_message_by_id: resolves many
    wa_message_id values to their wa_group_id in a single BigQuery call
    instead of one call per id. Used by the reaction-retry-queue path so a
    pull with many unresolved reactions issues one BQ query, not N."""
    from tap_lms.wagroupbot.bq import run_query

    ids = sorted({str(i) for i in wa_message_ids if i})
    if not ids:
        return {}

    sql = f"""
        SELECT id, wa_group_id
        FROM `{settings.bq_project}.{settings.bq_dataset}.{settings.bq_table}`
        WHERE CAST(id AS STRING) IN UNNEST(@message_ids)
        QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY inserted_at DESC) = 1
    """
    rows = run_query(
        sql,
        params={"message_ids": ids},
        param_types={"message_ids": "STRING"},
        max_bytes_billed=_bq_max_bytes_billed(settings),
    )
    return {str(r["id"]): r.get("wa_group_id") for r in rows}


def _query_bq_reactions(settings, since, until=None, limit=2000):
    from tap_lms.wagroupbot.bq import run_query

    conditions = ["r.inserted_at > @since"]
    params = {"since": since}
    if until:
        conditions.append("r.inserted_at <= @until")
        params["until"] = until

    sql = f"""
        SELECT r.id, r.bq_uuid, r.phone, r.reaction, r.wa_message_id, r.body, r.inserted_at,
               m.wa_group_id AS wa_group_id
        FROM `{settings.bq_project}.{settings.bq_dataset}.wa_reactions` r
        LEFT JOIN `{settings.bq_project}.{settings.bq_dataset}.{settings.bq_table}` m
          ON CAST(r.wa_message_id AS STRING) = CAST(m.id AS STRING)
        WHERE {" AND ".join(conditions)}
        QUALIFY ROW_NUMBER() OVER (PARTITION BY r.bq_uuid ORDER BY r.inserted_at DESC) = 1
        ORDER BY r.inserted_at ASC
        LIMIT {int(limit)}
    """
    return run_query(sql, params=params, max_bytes_billed=_bq_max_bytes_billed(settings))


def _query_bq_gcs_backfill(settings, since, limit=500):
    from tap_lms.wagroupbot.bq import run_query

    type_list = ", ".join(f"'{t}'" for t in GCS_BACKFILL_MIME_TYPES)
    sql = f"""
        SELECT {BQ_GCS_BACKFILL_COLUMNS}
        FROM `{settings.bq_project}.{settings.bq_dataset}.{settings.bq_table}`
        WHERE updated_at > @since
          AND gcs_url IS NOT NULL
          AND type IN ({type_list})
        ORDER BY updated_at ASC
        LIMIT {int(limit)}
    """
    return run_query(sql, params={"since": since}, max_bytes_billed=_bq_max_bytes_billed(settings))


def resolve_wa_group(glific_group_id):
    if not glific_group_id:
        return None
    return frappe.db.get_value("WA Group", {"glific_group_id": str(glific_group_id)}, "name")


def _ingest_message_rows(rows, prior_checkpoint, row_limit, settings):
    if not rows:
        return {
            "inserted": 0, "skipped": 0, "unresolved_group": 0, "ignored_staff": 0,
            "outbound_reconciled": 0, "outbound_external_recorded": 0, "truncated": False,
        }

    time_budget = settings.ingest_time_budget_seconds or 240
    started_at = now_datetime()
    last_checkpoint_write = started_at

    window_minutes = settings.turn_window_minutes or 45
    max_turn_items = settings.max_turn_items or DEFAULT_MAX_TURN_ITEMS

    newest_ts = prior_checkpoint
    inserted, skipped, unresolved_group, ignored_staff = 0, 0, 0, 0
    outbound_reconciled, outbound_external_recorded = 0, 0
    touched_turns = {}
    rollup_deltas = defaultdict(lambda: defaultdict(int))
    unresolved_group_ids_seen = set()

    processed = 0
    budget_exceeded = False

    for idx, row in enumerate(rows):
        # Time-based checkpoint instead of row-count-based: write progress
        # at most once every CHECKPOINT_INTERVAL_SECONDS of wall time, not
        # once every fixed number of rows. A fast pull that finishes in a
        # couple of seconds now performs zero or one mid-pull checkpoint
        # writes instead of several; a slow pull still checkpoints often
        # enough to bound crash-loss to roughly this interval.
        elapsed_since_checkpoint = frappe.utils.time_diff_in_seconds(now_datetime(), last_checkpoint_write)
        if idx > 0 and elapsed_since_checkpoint >= CHECKPOINT_INTERVAL_SECONDS:
            elapsed_total = frappe.utils.time_diff_in_seconds(now_datetime(), started_at)
            if elapsed_total > time_budget:
                budget_exceeded = True
                break
            refresh_lock("pull_messages", timeout=LOCK_HEARTBEAT_TIMEOUT_SECONDS)
            _set_settings_values({"bq_checkpoint_datetime": newest_ts})
            _flush_rollup_deltas(rollup_deltas)
            rollup_deltas.clear()
            frappe.db.commit()
            last_checkpoint_write = now_datetime()

        poll_choice = None
        has_poll_vote = False
        if row.get("poll_content") and row.get("flow") != "outbound":
            poll_choice, has_poll_vote = _extract_poll_choice(row.get("poll_content"), row.get("contact_phone"))
        event_type = classify_event_type(row, poll_choice, has_poll_vote)
        if event_type == "System":
            skipped += 1
            if row["inserted_at"] > newest_ts:
                newest_ts = row["inserted_at"]
            processed += 1
            continue

        direction = "Inbound" if row.get("flow") == "inbound" else "Outbound"
        wa_group = resolve_wa_group(row.get("wa_group_id"))
        if not wa_group:
            unresolved_group += 1
            unresolved_group_ids_seen.add(str(row.get("wa_group_id")))
            if row["inserted_at"] > newest_ts:
                newest_ts = row["inserted_at"]
            processed += 1
            continue

        if direction == "Inbound" and event_type != "Poll Sent":
            contact_phone = row.get("contact_phone")
            if not contact_phone:
                skipped += 1
            elif is_ignored_staff_number(contact_phone, settings):
                ignored_staff += 1
            else:
                turn_name, item_type, item_body, is_new_turn = _upsert_turn_item(
                    row, event_type, wa_group, contact_phone, window_minutes, max_turn_items, poll_choice
                )
                if turn_name:
                    touched_turns[turn_name] = (wa_group, contact_phone, item_type, item_body)
                    inserted += 1
                    _bucket_rollup_delta(rollup_deltas, wa_group, row["inserted_at"],
                                         COUNTER_BY_TYPE.get(event_type, "text_count"))
                    if event_type in ATTRIBUTABLE_EVENT_TYPES and (event_type == "Poll Response" or is_new_turn):
                        _attribute_campaign(turn_name, wa_group, event_type, row["inserted_at"])
                    _maybe_record_media(row, event_type, wa_group, turn_name)
                else:
                    skipped += 1
        elif direction == "Outbound":
            outcome = _upsert_outbound_message(row, wa_group, event_type)
            if outcome == "reconciled":
                outbound_reconciled += 1
                inserted += 1
            elif outcome == "external_recorded":
                outbound_external_recorded += 1
                inserted += 1
            elif outcome == "duplicate":
                inserted += 1
            else:
                skipped += 1
        else:
            skipped += 1

        if row["inserted_at"] > newest_ts:
            newest_ts = row["inserted_at"]
        processed += 1

    truncated = len(rows) == row_limit
    _set_settings_values({"bq_checkpoint_datetime": newest_ts})
    _flush_rollup_deltas(rollup_deltas)
    frappe.db.commit()

    if unresolved_group_ids_seen:
        frappe.log_error(
            title="WAGroupBot unresolved wa_group_id",
            message=(
                "These wa_group_id values from BigQuery did not match any WA Group.glific_group_id "
                "and their messages were dropped (checkpoint still advanced past them): "
                + ", ".join(sorted(unresolved_group_ids_seen)[:50])
                + ". Run Sync Groups, and confirm the id types match (BQ may return an "
                  "int, WA Group.glific_group_id is stored as text)."
            ),
        )

    if touched_turns:
        _dispatch_turn_followups(touched_turns, settings)

    if budget_exceeded and processed < len(rows):
        _enqueue_on_ingest_queue(
            "tap_lms.wagroupbot.inbound.pull_messages",
            enqueue_after_commit=True,
        )

    return {
        "inserted": inserted, "skipped": skipped, "unresolved_group": unresolved_group,
        "ignored_staff": ignored_staff,
        "outbound_reconciled": outbound_reconciled,
        "outbound_external_recorded": outbound_external_recorded,
        "truncated": truncated,
        "budget_exceeded": budget_exceeded,
        "message": "More than the row limit of new rows exist — click Pull Latest again after the cooldown."
            if truncated else None,
    }


def _upsert_outbound_message(row, wa_group, event_type):
    bq_id = str(row.get("id")) if row.get("id") is not None else None
    if not bq_id:
        return "skipped"

    existing_by_bq_id = frappe.db.get_value(
        SEND_MESSAGE_DOCTYPE, {"wa_group": wa_group, "glific_message_id": bq_id}, "name",
    )
    if existing_by_bq_id:
        bsp = (row.get("bsp_status") or "").lower()
        bq_status = {"delivered": "Delivered", "read": "Read", "sent": "Pending", "error": "Failed"}.get(bsp)
        if bq_status:
            frappe.db.set_value(SEND_MESSAGE_DOCTYPE, existing_by_bq_id, "bq_status", bq_status)
        return "duplicate"

    row_uuid = row.get("uuid")
    if row_uuid:
        matched = frappe.db.get_value(
            SEND_MESSAGE_DOCTYPE,
            {
                "wa_group": wa_group,
                "our_message_uuid": row_uuid,
                "origin": ["in", ("Batch Wave", "Direct Reply", "Auto Reply Rule")],
                "glific_message_id": ["in", ["", None]],
            },
            "name",
        )
        if matched:
            _apply_bq_echo(matched, row)
            return "reconciled"

    body = row.get("body")
    if body:
        since = add_to_date(row["inserted_at"], minutes=-SEND_ECHO_RECONCILE_LOOKBACK_MINUTES)
        # FIFO match: the OLDEST still-unmatched Send Message row with this
        # exact wa_group+body+status claims this echo first. If the same
        # text was sent more than once in the lookback window (a repeated
        # auto-reply phrase, a common "Thank you!" to two different
        # contacts, etc.), taking the oldest unmatched row first and letting
        # each subsequent echo claim the next-oldest is the only ordering
        # that can't misattribute an echo to a send that hasn't happened yet
        # and, for ties, matches sends to echoes in the order they actually
        # occurred rather than an arbitrary "most recent" guess.
        matched = frappe.db.get_value(
            SEND_MESSAGE_DOCTYPE,
            {
                "wa_group": wa_group,
                "origin": ["in", ("Batch Wave", "Direct Reply")],
                "message_body": body,
                "status": "Sent",
                "sent_at": [">=", since],
                "glific_message_id": ["in", ["", None]],
            },
            "name",
            order_by="sent_at asc",
        )
        if matched:
            _apply_bq_echo(matched, row)
            return "reconciled"

    _record_external_send(row, wa_group, bq_id, event_type)
    return "external_recorded"


def _apply_bq_echo(send_message_name, row):
    bsp = (row.get("bsp_status") or "").lower()
    bq_status = {"delivered": "Delivered", "read": "Read", "sent": "Pending", "error": "Failed"}.get(bsp)
    frappe.db.set_value(SEND_MESSAGE_DOCTYPE, send_message_name, {
        "glific_message_id": str(row.get("id")),
        "bq_status": bq_status or "Pending",
    })


def _record_external_send(row, wa_group, bq_id, event_type):
    bsp = (row.get("bsp_status") or "").lower()
    bq_status = {"delivered": "Delivered", "read": "Read", "sent": "Pending", "error": "Failed"}.get(bsp) or "Pending"

    message_body = row.get("body") or ""
    if not message_body and event_type in ("Poll Sent", "Poll Response"):
        message_body = _poll_question_text(row.get("poll_content")) or ""

    doc = frappe.new_doc(SEND_MESSAGE_DOCTYPE)
    doc.wa_group = wa_group
    doc.origin = "External"
    doc.message_body = message_body
    doc.media_url = _clean_gcs_url(row.get("gcs_url")) or row.get("media_url")
    doc.external_sender_phone = row.get("contact_phone")
    doc.status = "Sent"
    doc.bq_status = bq_status
    doc.sent_at = row.get("inserted_at")
    doc.sent_in_test_mode = 0
    doc.glific_message_id = bq_id
    doc.our_message_uuid = row.get("uuid")
    try:
        doc.insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        pass
    except Exception:
        frappe.log_error(
            title="WAGroupBot external send record failed",
            message=f"wa_group={wa_group} bq_id={bq_id}: {frappe.get_traceback()}",
        )


def _attribute_campaign(turn_name, wa_group, event_type, occurred_at):
    frappe.db.sql(
        """
        UPDATE "tabWA Group Turn" AS t
        SET related_campaign = c.batch,
            modified = now()
        FROM (
            SELECT sm.batch,
                   COALESCE(b.poll_response_window_hours, %(default_window)s) AS window_hours,
                   sm.sent_at, b.send_kind
            FROM "tabWA Send Message" sm
            JOIN "tabWA Send Batch" b ON b.name = sm.batch
            WHERE sm.wa_group = %(wa_group)s AND sm.origin = 'Batch Wave' AND sm.status = 'Sent'
              AND sm.sent_at <= %(occurred_at)s
            ORDER BY sm.sent_at DESC
            LIMIT 1
        ) AS c
        WHERE t.name = %(turn_name)s
          AND t.related_campaign IS NULL
          AND %(occurred_at)s <= c.sent_at + (
              CASE WHEN c.send_kind = 'Poll' THEN c.window_hours ELSE 24 END
              ) * INTERVAL '1 hour'
        """,
        {
            "turn_name": turn_name,
            "wa_group": wa_group,
            "occurred_at": occurred_at,
            "default_window": DEFAULT_POLL_ATTRIBUTION_WINDOW_HOURS,
        },
    )


def _maybe_record_media(row, event_type, wa_group, turn_name):
    if event_type not in ("Media", "Sticker"):
        return
    mime = extract_media_mime_type(row)
    is_sticker = (row.get("type") or "").lower() == "sticker"
    if mime not in RECORDABLE_MEDIA_MIME_TYPES and not is_sticker:
        return

    from tap_lms.tap_lms.doctype.wa_media.wa_media import upsert_media_record
    try:
        upsert_media_record(wa_group=wa_group, source_turn=turn_name, bq_id=str(row["id"]))
    except Exception:
        frappe.log_error(
            title="WAGroupBot media record failed",
            message=f"bq_id={row.get('id')} turn={turn_name}: {frappe.get_traceback()}",
        )


def _dispatch_turn_followups(touched_turns, settings):
    from tap_lms.wagroupbot.outbound import match_auto_reply_rule
    from tap_lms.wagroupbot.queues import enqueue as _wag_enqueue, AI_QUEUE

    ai_turn_names = []
    for turn_name, (wa_group, contact_phone, item_type, item_body) in touched_turns.items():
        if item_type in ("Text", "Media", "Voice", "Poll Response"):
            rule = match_auto_reply_rule(
                wa_group, item_type, item_body, contact_phone, bool(settings.ai_enabled),
            )
            if rule:
                _wag_enqueue(
                    "tap_lms.wagroupbot.outbound.send_auto_reply",
                    AI_QUEUE, wa_group=wa_group, contact_phone=contact_phone,
                    rule_name=rule.name,
                )
                continue
        ai_turn_names.append(turn_name)

    if ai_turn_names:
        from tap_lms.wagroupbot import ai
        ai.enqueue_turn_processing(ai_turn_names)


def _build_item_row(row, event_type, poll_choice=None):
    occurred_at = row["inserted_at"]
    body = row.get("body")
    return {
        "bq_id": str(row["id"]),
        "item_type": event_type,
        "body": body,
        "tagged_user_id": extract_tagged_user_id(body),
        "media_gcs_url": _clean_gcs_url(row.get("gcs_url")),
        "media_mime_type": extract_media_mime_type(row),
        "poll_choice": poll_choice,
        "transcript": None,
        "occurred_at": occurred_at,
    }


def _insert_turn_item_row(turn_name, idx, item):
    frappe.db.sql(
        """
        INSERT INTO "tabWA Group Turn Item"
            (name, parent, parenttype, parentfield, idx,
             bq_id, item_type, body, tagged_user_id, media_gcs_url, media_mime_type,
             poll_choice, transcript, occurred_at,
             creation, modified, owner, modified_by)
        VALUES
            (%(name)s, %(parent)s, 'WA Group Turn', 'turn_items', %(idx)s,
             %(bq_id)s, %(item_type)s, %(body)s, %(tagged_user_id)s, %(media_gcs_url)s, %(media_mime_type)s,
             %(poll_choice)s, %(transcript)s, %(occurred_at)s,
             now(), now(), %(user)s, %(user)s)
        """,
        {
            "name": frappe.generate_hash(length=10),
            "parent": turn_name,
            "idx": idx,
            "bq_id": item["bq_id"],
            "item_type": item["item_type"],
            "body": item.get("body"),
            "tagged_user_id": item.get("tagged_user_id"),
            "media_gcs_url": item.get("media_gcs_url"),
            "media_mime_type": item.get("media_mime_type"),
            "poll_choice": item.get("poll_choice"),
            "transcript": item.get("transcript"),
            "occurred_at": item["occurred_at"],
            "user": frappe.session.user,
        },
    )


def _recompute_composition_flags(turn_name):
    from tap_lms.tap_lms.doctype.wa_group_turn.wa_group_turn import ITEM_TYPE_TO_FLAG

    present = set(frappe.db.sql_list(
        'SELECT DISTINCT item_type FROM "tabWA Group Turn Item" WHERE parent = %(parent)s',
        {"parent": turn_name},
    ))
    updates = {fieldname: (1 if item_type in present else 0) for item_type, fieldname in ITEM_TYPE_TO_FLAG.items()}
    frappe.db.set_value(TURN_DOCTYPE, turn_name, updates)


def get_turn_item_bq_ids(turn_name):
    return set(frappe.db.sql_list(
        'SELECT bq_id FROM "tabWA Group Turn Item" WHERE parent = %(parent)s',
        {"parent": turn_name},
    ))


def get_turn_items(turn_name):
    return frappe.get_all(
        TURN_ITEM_DOCTYPE,
        filters={"parent": turn_name, "parenttype": "WA Group Turn"},
        fields=["bq_id", "item_type", "body", "tagged_user_id", "media_gcs_url",
                "media_mime_type", "poll_choice", "transcript", "occurred_at"],
        order_by="idx asc",
    )


def _upsert_turn_item(row, event_type, wa_group, contact_phone, window_minutes, max_turn_items, poll_choice=None):
    occurred_at = row["inserted_at"]
    body = row.get("body")
    item = _build_item_row(row, event_type, poll_choice)

    since = add_to_date(occurred_at, minutes=-window_minutes)
    turn_key = f"{wa_group}-{contact_phone}-{int(occurred_at.timestamp())}"
    user = frappe.session.user

    locked = frappe.db.sql(
        """
        SELECT name, item_count, is_closed
        FROM "tabWA Group Turn"
        WHERE wa_group = %(wa_group)s AND contact_phone = %(phone)s
          AND is_closed = 0 AND last_item_at >= %(since)s
        ORDER BY last_item_at DESC
        LIMIT 1
        FOR UPDATE
        """,
        {"wa_group": wa_group, "phone": contact_phone, "since": since},
        as_dict=True,
    )

    if locked:
        target = locked[0]
        existing_bq_ids = get_turn_item_bq_ids(target.name)
        if item["bq_id"] in existing_bq_ids:
            return target.name, event_type, body, False

        if target.item_count < max_turn_items:
            next_idx = target.item_count + 1
            _insert_turn_item_row(target.name, next_idx, item)
            new_count = next_idx
            will_close = 1 if new_count >= max_turn_items else target.is_closed
            frappe.db.sql(
                """
                UPDATE "tabWA Group Turn"
                SET item_count = %(count)s,
                    last_item_at = %(occurred_at)s,
                    is_closed = %(is_closed)s,
                    modified = now()
                WHERE name = %(name)s
                """,
                {
                    "name": target.name, "count": new_count,
                    "occurred_at": occurred_at, "is_closed": will_close,
                },
            )
            _recompute_composition_flags(target.name)
            return target.name, event_type, body, False

        overflow_key = f"{wa_group}-{contact_phone}-{int(occurred_at.timestamp())}-overflow"
        _insert_or_append_turn(overflow_key, wa_group, contact_phone, [item], occurred_at, user)
        return overflow_key, event_type, body, True

    created = _insert_or_append_turn(turn_key, wa_group, contact_phone, [item], occurred_at, user)
    return turn_key, event_type, body, created


def _insert_or_append_turn(turn_key, wa_group, contact_phone, new_items, occurred_at, user):
    existing = frappe.db.sql(
        """
        SELECT name, item_count, is_closed
        FROM "tabWA Group Turn"
        WHERE turn_key = %(key)s
        FOR UPDATE
        """,
        {"key": turn_key}, as_dict=True,
    )

    if not existing:
        frappe.db.sql(
            """
            INSERT INTO "tabWA Group Turn"
                (name, turn_key, wa_group, contact_phone, item_count,
                 last_item_at, turn_status, is_closed, creation, modified, owner, modified_by)
            VALUES
                (%(key)s, %(key)s, %(wa_group)s, %(phone)s, %(count)s,
                 %(occurred_at)s, 'Open', 0, now(), now(), %(user)s, %(user)s)
            ON CONFLICT (turn_key) DO NOTHING
            """,
            {
                "key": turn_key, "wa_group": wa_group, "phone": contact_phone,
                "count": len(new_items), "occurred_at": occurred_at, "user": user,
            },
        )
        recheck = frappe.db.sql(
            'SELECT name FROM "tabWA Group Turn" WHERE turn_key = %(key)s',
            {"key": turn_key}, as_dict=True,
        )
        if recheck:
            for idx, item in enumerate(new_items, start=1):
                _insert_turn_item_row(turn_key, idx, item)
            _recompute_composition_flags(turn_key)
            return True

    row = frappe.db.sql(
        """
        SELECT name, item_count, is_closed
        FROM "tabWA Group Turn"
        WHERE turn_key = %(key)s
        FOR UPDATE
        """,
        {"key": turn_key}, as_dict=True,
    )
    if not row:
        return True
    target = row[0]
    if target.is_closed:
        return False

    existing_bq_ids = get_turn_item_bq_ids(target.name)
    new_items = [it for it in new_items if it.get("bq_id") not in existing_bq_ids]
    if not new_items:
        return False

    next_idx = target.item_count + 1
    for offset, item in enumerate(new_items):
        _insert_turn_item_row(target.name, next_idx + offset, item)

    frappe.db.sql(
        """
        UPDATE "tabWA Group Turn"
        SET item_count = %(count)s,
            last_item_at = %(occurred_at)s,
            modified = now()
        WHERE name = %(name)s
        """,
        {
            "name": target.name, "count": target.item_count + len(new_items), "occurred_at": occurred_at,
        },
    )
    _recompute_composition_flags(target.name)
    return False


def _bucket_rollup_delta(rollup_deltas, wa_group, event_datetime, counter_field):
    if not wa_group or not event_datetime or not counter_field:
        return
    bucket_dt = event_datetime.replace(minute=0, second=0, microsecond=0)
    rollup_deltas[(wa_group, bucket_dt)][counter_field] += 1


def _bump_rollup(wa_group, event_datetime, counter_field):
    deltas = defaultdict(lambda: defaultdict(int))
    _bucket_rollup_delta(deltas, wa_group, event_datetime, counter_field)
    _flush_rollup_deltas(deltas)


def _flush_rollup_deltas(rollup_deltas):
    if not rollup_deltas:
        return
    user = frappe.session.user
    for (wa_group, bucket_dt), counters in rollup_deltas.items():
        rollup_key = f"{wa_group}-{bucket_dt.strftime('%Y-%m-%d-%H')}"
        upsert_clauses = ", ".join(
            f'{field} = COALESCE("tabWA Event Rollup".{field}, 0) + {amount}'
            for field, amount in counters.items()
        )
        columns = ", ".join(counters.keys())
        values = ", ".join(str(amount) for amount in counters.values())
        frappe.db.sql(
            f"""
            INSERT INTO "tabWA Event Rollup"
                (name, rollup_key, wa_group, bucket_datetime, {columns},
                 creation, modified, owner, modified_by)
            VALUES
                (%(key)s, %(key)s, %(wa_group)s, %(bucket_dt)s, {values},
                 now(), now(), %(user)s, %(user)s)
            ON CONFLICT (rollup_key) DO UPDATE SET
                {upsert_clauses},
                modified = now()
            """,
            {"key": rollup_key, "wa_group": wa_group, "bucket_dt": bucket_dt, "user": user},
        )


def close_expired_turns(settings=None):
    settings = settings or frappe.get_cached_doc(SETTINGS_DOCTYPE)
    window_minutes = settings.turn_window_minutes or 45
    cutoff = add_to_date(now_datetime(), minutes=-window_minutes, seconds=-CLOSE_GRACE_SECONDS)
    frappe.db.sql(
        """
        UPDATE "tabWA Group Turn"
        SET is_closed = 1
        WHERE is_closed = 0 AND last_item_at < %(cutoff)s
        """,
        {"cutoff": cutoff},
    )
    frappe.db.commit()


def mark_unreconciled_sends_for_retry():
    frappe.db.sql(
        """
        UPDATE "tabWA Send Message"
        SET error = COALESCE(error, '')
        WHERE status = 'Sent'
          AND origin IN ('Batch Wave', 'Direct Reply')
          AND (glific_message_id IS NULL OR glific_message_id = '')
          AND sent_at >= %(cutoff)s
        """,
        {"cutoff": add_to_date(now_datetime(), hours=-24)},
    )
    stuck = frappe.db.sql(
        """
        SELECT name, wa_group, origin, message_body, sent_at FROM "tabWA Send Message"
        WHERE status = 'Sent'
          AND origin IN ('Batch Wave', 'Direct Reply')
          AND (glific_message_id IS NULL OR glific_message_id = '')
          AND sent_at < %(stuck_cutoff)s
          AND sent_at >= %(cutoff)s
        """,
        {"stuck_cutoff": add_to_date(now_datetime(), hours=-1), "cutoff": add_to_date(now_datetime(), hours=-24)},
        as_dict=True,
    )
    if stuck:
        frappe.log_error(
            title="WAGroupBot: sends never reconciled to a BQ message id",
            message="\n".join(
                f"{r.name} wa_group={r.wa_group} origin={r.origin} sent_at={r.sent_at} "
                f"body={(r.message_body or '')[:80]!r}"
                for r in stuck
            ),
        )
    frappe.db.commit()


def _resolve_reacted_on_our_message(wa_group, reacted_message_bq_id):
    if not reacted_message_bq_id:
        return False, None, "text"

    bq_id = str(reacted_message_bq_id)

    sent = frappe.db.get_value(
        SEND_MESSAGE_DOCTYPE, {"wa_group": wa_group, "glific_message_id": bq_id},
        ["media_url"], as_dict=True,
    )
    if sent:
        media_url = sent.media_url
        msg_type = "image" if media_url else "text"
        return True, media_url, msg_type

    item = frappe.db.sql(
        """
        SELECT ti.media_gcs_url, ti.media_mime_type
        FROM "tabWA Group Turn Item" ti
        JOIN "tabWA Group Turn" t ON t.name = ti.parent
        WHERE t.wa_group = %(wa_group)s AND ti.bq_id = %(bq_id)s
        LIMIT 1
        """,
        {"wa_group": wa_group, "bq_id": bq_id}, as_dict=True,
    )
    if item:
        row = item[0]
        return False, row.media_gcs_url, (row.media_mime_type or "text")

    return False, None, "text"


def ensure_reaction_unique_index():
    try:
        frappe.db.sql(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS wa_group_reaction_unique_key
            ON "tabWA Group Reaction" (wa_group, reacted_message_bq_id, contact_phone)
            """
        )
        frappe.db.commit()
    except Exception:
        frappe.log_error(
            title="WAGroupBot ensure_reaction_unique_index failed",
            message=frappe.get_traceback(),
        )


def _resolve_wa_group_for_reaction(row, settings, bq_group_lookup=None):
    """bq_group_lookup, when provided, is a pre-fetched {wa_message_id_str:
    wa_group_id} dict (see _query_bq_messages_by_ids) so this never issues
    its own per-row BigQuery call during batch ingestion. Only falls back to
    a live single-id BQ lookup when no pre-fetched map was supplied (e.g.
    the manual "retry one" dashboard action on a single queued reaction)."""
    wa_group = resolve_wa_group(row.get("wa_group_id"))
    if wa_group:
        return wa_group

    wa_message_id = row.get("wa_message_id")
    if not wa_message_id:
        return None

    if bq_group_lookup is not None:
        glific_group_id = bq_group_lookup.get(str(wa_message_id))
        return resolve_wa_group(glific_group_id) if glific_group_id else None

    try:
        bq_rows = _query_bq_messages_by_ids(settings, [wa_message_id])
    except Exception:
        frappe.log_error(
            title="WAGroupBot reaction group backfill lookup failed",
            message=f"wa_message_id={wa_message_id}: {frappe.get_traceback()}",
        )
        return None

    glific_group_id = bq_rows.get(str(wa_message_id))
    return resolve_wa_group(glific_group_id) if glific_group_id else None


def ingest_reaction(row, settings=None, bq_group_lookup=None):
    settings = settings or frappe.get_cached_doc(SETTINGS_DOCTYPE)
    wa_group = _resolve_wa_group_for_reaction(row, settings, bq_group_lookup=bq_group_lookup)
    if not wa_group:
        return False, "unresolved_group"

    reacted_message_bq_id = row.get("wa_message_id")
    contact_phone = row.get("phone")
    raw_emoji = row.get("reaction")
    if not reacted_message_bq_id or not contact_phone or not raw_emoji:
        return False, "missing_fields"

    if is_ignored_staff_number(contact_phone, settings):
        return False, "ignored_staff"

    normalized = normalize_emoji(raw_emoji)
    reacted_on_our_message, reacted_media_url, reacted_msg_type = _resolve_reacted_on_our_message(
        wa_group, reacted_message_bq_id,
    )

    try:
        frappe.db.sql(
            """
            INSERT INTO "tabWA Group Reaction"
                (name, wa_group, contact_phone, reaction_emoji, normalized_emoji, reacted_message_bq_id,
                 occurred_at, reacted_message_body, reacted_message_media_url, reacted_message_type,
                 bq_uuid, reacted_on_our_message, creation, modified, owner, modified_by)
            VALUES
                (%(name)s, %(wa_group)s, %(phone)s, %(emoji)s, %(normalized_emoji)s, %(bq_id)s,
                 %(occurred_at)s, %(body)s, %(media_url)s, %(msg_type)s,
                 %(bq_uuid)s, %(reacted_on_our_message)s, now(), now(), %(user)s, %(user)s)
            ON CONFLICT (wa_group, reacted_message_bq_id, contact_phone) DO UPDATE SET
                reaction_emoji = EXCLUDED.reaction_emoji,
                normalized_emoji = EXCLUDED.normalized_emoji,
                occurred_at = EXCLUDED.occurred_at,
                reacted_message_body = EXCLUDED.reacted_message_body,
                reacted_message_media_url = EXCLUDED.reacted_message_media_url,
                reacted_message_type = EXCLUDED.reacted_message_type,
                bq_uuid = EXCLUDED.bq_uuid,
                reacted_on_our_message = EXCLUDED.reacted_on_our_message,
                modified = now()
            """,
            {
                "name": frappe.generate_hash(length=10),
                "wa_group": wa_group,
                "phone": contact_phone,
                "emoji": raw_emoji,
                "normalized_emoji": normalized,
                "bq_id": str(reacted_message_bq_id),
                "occurred_at": row.get("inserted_at"),
                "body": row.get("body"),
                "media_url": reacted_media_url,
                "msg_type": reacted_msg_type,
                "bq_uuid": row.get("bq_uuid"),
                "reacted_on_our_message": 1 if reacted_on_our_message else 0,
                "user": frappe.session.user,
            },
        )
    except Exception:
        frappe.log_error(title="WAGroupBot reaction upsert failed",
                          message=f"wa_group={wa_group} bq_id={reacted_message_bq_id} phone={contact_phone}: {frappe.get_traceback()}")
        return False, "db_error"

    return True, None


def _queue_unresolved_reaction(row):
    bq_uuid = row.get("bq_uuid")
    if not bq_uuid:
        return
    existing = frappe.db.exists(REACTION_RETRY_QUEUE_DOCTYPE, {"bq_uuid": bq_uuid})
    if existing:
        return
    doc = frappe.new_doc(REACTION_RETRY_QUEUE_DOCTYPE)
    doc.bq_uuid = bq_uuid
    doc.wa_message_id = str(row.get("wa_message_id") or "")
    doc.phone = row.get("phone")
    doc.reaction = row.get("reaction")
    doc.body = row.get("body")
    doc.inserted_at = row.get("inserted_at")
    doc.retry_attempts = 0
    try:
        doc.insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        pass
    except Exception:
        frappe.log_error(
            title="WAGroupBot reaction retry queue insert failed",
            message=f"bq_uuid={bq_uuid}: {frappe.get_traceback()}",
        )


def _retry_queued_reactions(settings):
    if not frappe.db.table_exists(REACTION_RETRY_QUEUE_DOCTYPE):
        return {"retried": 0, "resolved": 0}

    queued = frappe.get_all(
        REACTION_RETRY_QUEUE_DOCTYPE,
        filters={"retry_attempts": ["<", MAX_REACTION_RETRY_ATTEMPTS]},
        fields=["name", "bq_uuid", "wa_message_id", "phone", "reaction", "body", "inserted_at", "retry_attempts"],
        limit_page_length=500,
    )
    if not queued:
        return {"retried": 0, "resolved": 0}

    # Batch-resolve every queued row's wa_group_id in ONE BigQuery call
    # instead of one call per row (previously: ingest_reaction ->
    # _resolve_wa_group_for_reaction -> _query_bq_message_by_id, called
    # once per unresolved row — up to 500 individual billed BQ queries in
    # the worst case). This is the single most expensive fix in the audit.
    message_ids = [q.wa_message_id for q in queued if q.wa_message_id]
    try:
        bq_group_lookup = _query_bq_messages_by_ids(settings, message_ids) if message_ids else {}
    except Exception:
        frappe.log_error(
            title="WAGroupBot batched reaction-retry BQ lookup failed",
            message=frappe.get_traceback(),
        )
        bq_group_lookup = {}

    resolved = 0
    for queued_row in queued:
        row = {
            "bq_uuid": queued_row.bq_uuid,
            "wa_message_id": queued_row.wa_message_id,
            "phone": queued_row.phone,
            "reaction": queued_row.reaction,
            "body": queued_row.body,
            "inserted_at": queued_row.inserted_at,
            "wa_group_id": None,
        }
        ok, reason = ingest_reaction(row, settings, bq_group_lookup=bq_group_lookup)
        if ok:
            resolved += 1
            frappe.delete_doc(REACTION_RETRY_QUEUE_DOCTYPE, queued_row.name, ignore_permissions=True)
        else:
            frappe.db.set_value(REACTION_RETRY_QUEUE_DOCTYPE, queued_row.name, "retry_attempts",
                                 queued_row.retry_attempts + 1)

    frappe.db.commit()
    return {"retried": len(queued), "resolved": resolved}


def _ingest_reaction_rows(rows, prior_checkpoint, until=None, settings=None):
    ensure_reaction_unique_index()
    settings = settings or frappe.get_cached_doc(SETTINGS_DOCTYPE)

    retry_result = _retry_queued_reactions(settings)

    if not rows:
        if until and until > prior_checkpoint:
            _set_settings_values({"bq_reaction_checkpoint_datetime": until})
            frappe.db.commit()
        return {
            "inserted": 0, "ignored_staff": 0, "unresolved_group": 0, "missing_fields": 0, "failed": 0,
            "queued": 0, "queue_retried": retry_result["retried"], "queue_resolved": retry_result["resolved"],
        }

    newest_ts = prior_checkpoint
    inserted = 0
    ignored_staff = 0
    unresolved_group = 0
    missing_fields = 0
    failed = 0
    queued = 0
    unresolved_group_ids_seen = set()
    rollup_deltas = defaultdict(lambda: defaultdict(int))

    for row in rows:
        ok, reason = ingest_reaction(row, settings)
        if ok:
            inserted += 1
            wa_group = _resolve_wa_group_for_reaction(row, settings)
            _bucket_rollup_delta(rollup_deltas, wa_group, row["inserted_at"], "reaction_count")
        elif reason == "ignored_staff":
            ignored_staff += 1
        elif reason == "unresolved_group":
            unresolved_group += 1
            unresolved_group_ids_seen.add(str(row.get("wa_group_id")))
            _queue_unresolved_reaction(row)
            queued += 1
        elif reason == "missing_fields":
            missing_fields += 1
        elif reason == "db_error":
            failed += 1
        if row["inserted_at"] > newest_ts:
            newest_ts = row["inserted_at"]

    _set_settings_values({"bq_reaction_checkpoint_datetime": newest_ts})
    _flush_rollup_deltas(rollup_deltas)
    frappe.db.commit()

    if unresolved_group_ids_seen:
        frappe.log_error(
            title="WAGroupBot unresolved wa_group_id (reactions)",
            message=(
                "These wa_group_id values from BigQuery reaction rows did not match any "
                "WA Group.glific_group_id and their reactions were queued for retry: "
                + ", ".join(sorted(unresolved_group_ids_seen)[:50])
            ),
        )

    return {
        "inserted": inserted, "ignored_staff": ignored_staff,
        "unresolved_group": unresolved_group, "missing_fields": missing_fields, "failed": failed,
        "queued": queued, "queue_retried": retry_result["retried"], "queue_resolved": retry_result["resolved"],
    }


def _ingest_gcs_backfill_rows(rows, prior_checkpoint):
    if not rows:
        return {"backfilled": 0}

    from tap_lms.tap_lms.doctype.wa_group_turn_item.wa_group_turn_item import backfill_media_gcs_url

    newest_ts = prior_checkpoint
    backfilled = 0
    for row in rows:
        cleaned = _clean_gcs_url(row.get("gcs_url"))
        if cleaned and backfill_media_gcs_url(str(row["id"]), cleaned):
            backfilled += 1
        if row["updated_at"] > newest_ts:
            newest_ts = row["updated_at"]

    _set_settings_values({"bq_gcs_backfill_checkpoint_datetime": newest_ts})
    frappe.db.commit()
    return {"backfilled": backfilled}


def reactions_for_turn(turn_name):
    item_bq_ids = list(get_turn_item_bq_ids(turn_name))
    if not item_bq_ids:
        return []

    wa_group = frappe.db.get_value(TURN_DOCTYPE, turn_name, "wa_group")
    return frappe.get_all(
        REACTION_DOCTYPE,
        filters={"wa_group": wa_group, "reacted_message_bq_id": ["in", item_bq_ids]},
        fields=["reaction_emoji", "normalized_emoji", "contact_phone", "occurred_at", "reacted_message_bq_id"],
        order_by="occurred_at asc",
    )


def reactions_on_tagged_messages(wa_group=None, settings=None, limit=200):
    my_tag_id = get_my_tag_id(settings)
    if not my_tag_id:
        return []

    conditions = ["ti.tagged_user_id = %(my_tag_id)s"]
    params = {"my_tag_id": my_tag_id, "limit": int(limit)}
    if wa_group:
        conditions.append("t.wa_group = %(wa_group)s")
        params["wa_group"] = wa_group

    return frappe.db.sql(
        f"""
        SELECT
            r.name AS reaction_name,
            r.wa_group,
            r.reaction_emoji,
            r.normalized_emoji,
            r.contact_phone AS reactor_phone,
            r.occurred_at AS reacted_at,
            r.reacted_message_bq_id AS bq_id,
            t.name AS turn_name,
            t.contact_phone AS tagged_message_sender
        FROM "tabWA Group Turn Item" ti
        JOIN "tabWA Group Turn" t ON t.name = ti.parent
        JOIN "tabWA Group Reaction" r
            ON r.wa_group = t.wa_group AND r.reacted_message_bq_id = ti.bq_id
        WHERE {" AND ".join(conditions)}
        ORDER BY r.occurred_at DESC
        LIMIT %(limit)s
        """,
        params,
        as_dict=True,
    )


def tagged_message_turns(wa_group=None, settings=None, start=0, page_length=25):
    """Server-side query for 'who tagged @me', filtered directly on the
    indexed tagged_user_id column instead of scanning every turn's items in
    the browser. Returns turns that have at least one item tagged to the
    configured My Tag ID, newest-tagged-item first, paginated."""
    my_tag_id = get_my_tag_id(settings)
    if not my_tag_id:
        return {"rows": [], "has_more": False}

    conditions = ["ti.tagged_user_id = %(my_tag_id)s"]
    params = {
        "my_tag_id": my_tag_id,
        "start": max(int(start), 0),
        "page_length": min(int(page_length), 100) + 1,
    }
    if wa_group:
        conditions.append("t.wa_group = %(wa_group)s")
        params["wa_group"] = wa_group

    rows = frappe.db.sql(
        f"""
        SELECT
            ti.bq_id, ti.body, ti.occurred_at,
            t.name AS turn_name, t.wa_group, t.contact_phone, t.turn_status
        FROM "tabWA Group Turn Item" ti
        JOIN "tabWA Group Turn" t ON t.name = ti.parent
        WHERE {" AND ".join(conditions)}
        ORDER BY ti.occurred_at DESC
        LIMIT %(page_length)s OFFSET %(start)s
        """,
        params,
        as_dict=True,
    )
    has_more = len(rows) > (params["page_length"] - 1)
    return {"rows": rows[: params["page_length"] - 1], "has_more": has_more}


def reaction_emoji_breakdown(wa_group=None, wa_group_names=None, date_from=None, date_to=None, limit=50):
    conditions = ["1=1"]
    params = {"limit": int(limit or 50)}
    if wa_group:
        conditions.append("wa_group = %(wa_group)s")
        params["wa_group"] = wa_group
    elif wa_group_names is not None:
        if not wa_group_names:
            return []
        conditions.append("wa_group IN %(wa_group_names)s")
        params["wa_group_names"] = tuple(wa_group_names)
    if date_from:
        date_from = str(date_from)
        conditions.append("occurred_at >= %(date_from)s")
        params["date_from"] = date_from if " " in date_from else f"{date_from} 00:00:00"
    if date_to:
        date_to = str(date_to)
        conditions.append("occurred_at <= %(date_to)s")
        params["date_to"] = date_to if " " in date_to else f"{date_to} 23:59:59"

    return frappe.db.sql(
        f"""
        SELECT wa_group, normalized_emoji AS emoji, COUNT(*) AS reaction_count,
               SUM(CASE WHEN reacted_on_our_message = 1 THEN 1 ELSE 0 END) AS reacted_on_our_message_count,
               MAX(occurred_at) AS last_reacted_at
        FROM "tabWA Group Reaction"
        WHERE {" AND ".join(conditions)}
        GROUP BY wa_group, normalized_emoji
        ORDER BY reaction_count DESC
        LIMIT %(limit)s
        """,
        params,
        as_dict=True,
    )


def resolve_contact(phone):
    if not phone:
        return {"kind": None, "display": phone, "language": None}

    teacher = frappe.db.get_value("Teacher", {"phone_number": phone}, ["name", "first_name", "language"], as_dict=True)
    if teacher:
        return {"kind": "Teacher", "name": teacher.name, "display": teacher.first_name, "language": teacher.language}

    student = frappe.db.get_value("Student", {"phone": phone}, ["name", "name1", "language"], as_dict=True)
    if student:
        return {"kind": "Student", "name": student.name, "display": student.name1, "language": student.language}

    return {"kind": None, "display": phone, "language": None}


def bulk_resolve_contacts(phones):
    phones = list({p for p in phones if p})
    if not phones:
        return {}

    result = {}
    for t in frappe.get_all("Teacher", filters={"phone_number": ["in", phones]},
                             fields=["name", "phone_number", "first_name", "language"]):
        result[t.phone_number] = {"kind": "Teacher", "name": t.name, "display": t.first_name, "language": t.language}
    for s in frappe.get_all("Student", filters={"phone": ["in", phones]},
                             fields=["name", "phone", "name1", "language"]):
        if s.phone not in result:
            result[s.phone] = {"kind": "Student", "name": s.name, "display": s.name1, "language": s.language}

    for phone in phones:
        if phone not in result:
            result[phone] = {"kind": None, "name": None, "display": phone, "language": None}
    return result


def get_reply_for_turn(turn_name):
    return frappe.db.get_value(
        SEND_MESSAGE_DOCTYPE, {"source_turn": turn_name, "origin": "Direct Reply"},
        ["name", "glific_message_id", "sent_at"], as_dict=True, order_by="sent_at desc",
    )


def has_recent_image_reply_for_contact(wa_group, contact_phone, since_minutes, exclude_turn=None):
    since = add_to_date(now_datetime(), minutes=-since_minutes)
    conditions = [
        "wa_group = %(wa_group)s", "contact_phone = %(phone)s",
        "last_item_at >= %(since)s", "ai_tags LIKE %(image_reply_tag)s",
    ]
    params = {
        "wa_group": wa_group, "phone": contact_phone, "since": since,
        "image_reply_tag": "%image_reply_sent%",
    }
    if exclude_turn:
        conditions.append("name != %(exclude_turn)s")
        params["exclude_turn"] = exclude_turn

    row = frappe.db.sql(
        f"""
        SELECT name FROM "tabWA Group Turn"
        WHERE {" AND ".join(conditions)}
        LIMIT 1
        """,
        params,
    )
    return bool(row)


def has_tagged_us(turn_name, settings=None):
    my_tag_id = get_my_tag_id(settings)
    if not my_tag_id:
        return False
    return bool(frappe.db.exists(TURN_ITEM_DOCTYPE, {
        "parent": turn_name, "parenttype": "WA Group Turn", "tagged_user_id": my_tag_id,
    }))