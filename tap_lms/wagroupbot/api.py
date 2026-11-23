import json
import mimetypes
from functools import wraps

import frappe
import requests

from tap_lms.wagroupbot.filters import (
    parse_filters,
    apply_geo_filters,
    apply_date_range,
    apply_turn_status,
    apply_tag,
    apply_ai_urgency,
    apply_media_category,
    apply_contact_phone,
    apply_send_status,
    apply_send_origin,
)
from tap_lms.wagroupbot.queues import enqueue as _wag_enqueue, INGEST_QUEUE

SETTINGS_DOCTYPE = "WA Bot Settings"
TURN_DOCTYPE = "WA Group Turn"
SEND_BATCH_DOCTYPE = "WA Send Batch"
SEND_MESSAGE_DOCTYPE = "WA Send Message"
REACTION_DOCTYPE = "WA Group Reaction"
ROLLUP_DOCTYPE = "WA Event Rollup"
MEDIA_DOCTYPE = "WA Media"
REACTION_RETRY_QUEUE_DOCTYPE = "WA Reaction Retry Queue"

GRANULARITY_TRUNC = {"hour": "hour", "day": "day"}
MEDIA_CATEGORIES = ("School Activity", "Poster", "Support", "Event", "Unnecessary", "Other")


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def glific_safe(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from tap_lms.wagroupbot.glific import GlificManualTokenError, GlificAPIError, GlificTerminalError
        try:
            return fn(*args, **kwargs)
        except GlificManualTokenError as e:
            frappe.throw(str(e), title="Glific Token Expired")
        except (GlificAPIError, GlificTerminalError) as e:
            frappe.throw(f"Glific error: {e}", title="Glific Error")
    return wrapper


def _bulk_turn_items_json(turn_names):
    turn_names = list({t for t in (turn_names or []) if t})
    if not turn_names:
        return {}

    rows = frappe.db.sql(
        """
        SELECT parent, idx, bq_id, item_type, body, tagged_user_id, media_gcs_url,
               media_mime_type, poll_choice, transcript, occurred_at
        FROM "tabWA Group Turn Item"
        WHERE parent IN %(names)s
        ORDER BY parent, idx ASC
        """,
        {"names": tuple(turn_names)}, as_dict=True,
    )

    grouped = {}
    for r in rows:
        occurred_at = r.occurred_at
        if hasattr(occurred_at, "isoformat"):
            occurred_at = occurred_at.isoformat()
        item = {
            "bq_id": r.bq_id,
            "item_type": r.item_type,
            "body": r.body,
            "tagged_user_id": r.tagged_user_id,
            "media_gcs_url": r.media_gcs_url,
            "media_mime_type": r.media_mime_type,
            "poll_choice": r.poll_choice,
            "transcript": r.transcript,
            "occurred_at": occurred_at,
        }
        grouped.setdefault(r.parent, []).append(item)

    return {name: json.dumps(grouped.get(name, [])) for name in turn_names}


@frappe.whitelist()
def pull_latest_messages():
    frappe.only_for("System Manager")
    _wag_enqueue("tap_lms.wagroupbot.inbound.pull_messages", INGEST_QUEUE)
    return {"status": "queued", "message": "Pull triggered in background."}


@frappe.whitelist()
def auto_pull_if_due():
    frappe.only_for("System Manager")
    settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
    from tap_lms.wagroupbot.inbound import _poll_lock_remaining_minutes
    remaining = _poll_lock_remaining_minutes(settings)
    if remaining > 0:
        return {"status": "skipped", "remaining_minutes": round(remaining, 1)}
    _wag_enqueue("tap_lms.wagroupbot.inbound.pull_messages", INGEST_QUEUE)
    return {"status": "queued"}


@frappe.whitelist()
def pull_messages_for_range(date_from, date_to, wa_group=None):
    frappe.only_for("System Manager")
    _wag_enqueue(
        "tap_lms.wagroupbot.inbound.pull_messages_for_range",
        INGEST_QUEUE, date_from=date_from, date_to=date_to, wa_group=wa_group,
    )
    return {"status": "queued", "message": "Range pull triggered in background."}


@frappe.whitelist()
def pull_wa_groups_and_phones():
    frappe.only_for("System Manager")
    _wag_enqueue("tap_lms.wagroupbot.directory.pull_wa_groups_and_phones", INGEST_QUEUE)
    return {"status": "queued", "message": "Directory sync triggered in background."}


@frappe.whitelist()
def test_glific_connection():
    from tap_lms.wagroupbot.glific import GlificClient
    return GlificClient().test_connection()


@frappe.whitelist()
@glific_safe
def preview_dispatch_targets(target_type, wa_group=None, wa_group_collection=None,
                              district=None, city=None, state=None, school=None):
    from tap_lms.wagroupbot.outbound import preview_dispatch_targets as _preview
    return _preview(
        target_type, wa_group=wa_group, wa_group_collection=wa_group_collection,
        district=district, city=city, state=state, school=school,
    )


@frappe.whitelist()
def save_send_batch_draft(batch_name=None, **fields):
    frappe.only_for("System Manager")
    fields.pop("cmd", None)

    raw_poll_languages = fields.pop("poll_languages", None)
    if isinstance(raw_poll_languages, str):
        raw_poll_languages = json.loads(raw_poll_languages) if raw_poll_languages else None

    is_multi = _to_bool(fields.get("is_multi_language_poll"))
    fields["is_multi_language_poll"] = 1 if is_multi else 0

    if is_multi:
        fields["poll_uuid"] = None
    else:
        fields["poll_uuid"] = fields.get("poll_uuid") or None

    if batch_name:
        doc = frappe.get_doc(SEND_BATCH_DOCTYPE, batch_name)
        if doc.status not in ("Draft", "Scheduled"):
            frappe.throw("Only a Draft or Scheduled batch's content can be updated.")
        was_scheduled = doc.status == "Scheduled"
        doc.update(fields)
        if not is_multi:
            doc.set("poll_languages", [])
    else:
        doc = frappe.new_doc(SEND_BATCH_DOCTYPE)
        doc.update(fields)
        was_scheduled = False

    doc.save(ignore_permissions=True)

    if is_multi and raw_poll_languages is not None:
        _set_batch_poll_languages(doc.name, raw_poll_languages)
        doc.reload()

    if was_scheduled:
        from tap_lms.wagroupbot.outbound import expand_send_batch
        expand_send_batch(doc.name)
        doc.reload()

    frappe.db.commit()
    return {"name": doc.name, "status": doc.status}


def _set_batch_poll_languages(batch_name, rows):
    doc = frappe.get_doc(SEND_BATCH_DOCTYPE, batch_name)
    doc.set("poll_languages", [])
    for r in rows:
        doc.append("poll_languages", {
            "language": r.get("language"),
            "poll_uuid": r.get("poll_uuid"),
            "is_default": 1 if r.get("is_default") else 0,
        })
    doc.is_multi_language_poll = 1
    doc.save(ignore_permissions=True)
    _sync_poll_label_for_batch(doc)


def _sync_poll_label_for_batch(doc):
    from tap_lms.tap_lms.doctype.wa_poll_label.wa_poll_label import sync_poll_labels
    try:
        sync_poll_labels()
    except Exception:
        frappe.log_error(title="WAGroupBot poll label sync failed", message=frappe.get_traceback())


@frappe.whitelist()
def set_batch_poll_languages(batch_name, rows):
    frappe.only_for("System Manager")
    if isinstance(rows, str):
        rows = json.loads(rows)
    doc = frappe.get_doc(SEND_BATCH_DOCTYPE, batch_name)
    if doc.status not in ("Draft", "Scheduled"):
        frappe.throw("Only a Draft or Scheduled batch can have its poll language rows set.")
    _set_batch_poll_languages(batch_name, rows)
    return {"status": "ok"}


@frappe.whitelist()
@glific_safe
def schedule_send_batch(batch_name, scheduled_send_at=None):
    frappe.only_for("System Manager")
    from tap_lms.wagroupbot.outbound import expand_send_batch
    doc = frappe.get_doc(SEND_BATCH_DOCTYPE, batch_name)
    if doc.status != "Draft":
        frappe.throw("Only a Draft batch can be scheduled.")
    doc.scheduled_send_at = scheduled_send_at or frappe.utils.now_datetime()
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    expand_send_batch(batch_name)
    doc.reload()
    return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def unschedule_send_batch(batch_name):
    frappe.only_for("System Manager")
    doc = frappe.get_doc(SEND_BATCH_DOCTYPE, batch_name)
    if doc.status != "Scheduled":
        frappe.throw("Only a Scheduled batch can be unscheduled.")
    if frappe.db.exists(SEND_MESSAGE_DOCTYPE, {"batch": batch_name, "origin": "Batch Wave"}):
        frappe.throw("This batch has already started sending and cannot be moved back to Draft.")
    doc.status = "Draft"
    doc.scheduled_send_at = None
    doc.resolved_target_groups = None
    doc.total_groups = None
    doc.waves_total = None
    doc.waves_sent = None
    doc.next_wave_at = None
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def cancel_send_batch(batch_name):
    frappe.only_for("System Manager")
    from tap_lms.wagroupbot.outbound import cancel_send_batch as _cancel
    doc = _cancel(batch_name)
    frappe.db.commit()
    return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
@glific_safe
def run_due_send_waves():
    from tap_lms.wagroupbot.outbound import run_due_send_waves as _run
    return _run()


@frappe.whitelist()
def get_send_batch_progress(batch_name):
    doc = frappe.db.get_value(
        SEND_BATCH_DOCTYPE, batch_name,
        ["name", "status", "send_kind", "total_groups", "waves_total", "waves_sent",
         "next_wave_at", "wave_size", "wave_gap_minutes", "scheduled_send_at", "cancelled_at"],
        as_dict=True,
    )
    if not doc:
        frappe.throw("Send batch not found.")

    counts = frappe.db.sql(
        """
        SELECT status, COUNT(*) AS cnt
        FROM "tabWA Send Message"
        WHERE batch = %(batch)s AND origin = 'Batch Wave'
        GROUP BY status
        """,
        {"batch": batch_name}, as_dict=True,
    )
    doc["sent_count"] = next((c.cnt for c in counts if c.status == "Sent"), 0)
    doc["failed_count"] = next((c.cnt for c in counts if c.status == "Failed"), 0)
    return doc


@frappe.whitelist()
def list_send_batches(filters=None, start=0, page_length=10):
    filters = parse_filters(filters)
    limit = min(int(page_length), 100)
    start = max(int(start), 0)

    conditions, params = ["1=1"], {"limit": limit + 1, "start": start}
    conditions, params = apply_send_status(conditions, params, filters)

    rows = frappe.db.sql(
        f"""
        SELECT name, title, send_kind, target_type, wa_group, wa_group_collection,
               district, city, state, school, status, scheduled_send_at, next_wave_at,
               total_groups, waves_total, waves_sent, real_target_group_count,
               sent_in_test_mode, message_body, media_url, media_file, glific_flow_id, poll_uuid,
               is_multi_language_poll, cancelled_at, modified
        FROM "tabWA Send Batch"
        WHERE {" AND ".join(conditions)}
        ORDER BY modified DESC
        LIMIT %(limit)s OFFSET %(start)s
        """,
        params, as_dict=True,
    )
    has_more = len(rows) > limit
    rows = rows[:limit]

    batch_names = [r.name for r in rows]
    send_counts = {}
    if batch_names:
        for c in frappe.db.sql(
            """
            SELECT batch, status, COUNT(*) AS cnt
            FROM "tabWA Send Message"
            WHERE batch IN %(names)s AND origin = 'Batch Wave'
            GROUP BY batch, status
            """,
            {"names": tuple(batch_names)}, as_dict=True,
        ):
            send_counts.setdefault(c.batch, {})[c.status] = c.cnt

    group_names_map = {g.name: g.group_name for g in frappe.get_all(
        "WA Group", filters={"name": ["in", list({r.wa_group for r in rows if r.wa_group})]},
        fields=["name", "group_name"],
    )} if rows else {}

    poll_uuids = [r.poll_uuid for r in rows if r.poll_uuid]
    from tap_lms.tap_lms.doctype.wa_poll_label.wa_poll_label import bulk_get_poll_labels
    label_lookup = bulk_get_poll_labels(poll_uuids) if poll_uuids else {}

    for r in rows:
        target = r.wa_group or r.wa_group_collection \
            or " / ".join(filter(None, [r.state, r.district, r.city, r.school])) or ""
        r["target_label"] = group_names_map.get(r.wa_group, r.wa_group) if r.wa_group else target
        counts = send_counts.get(r.name, {})
        r["sent_count"] = counts.get("Sent", 0)
        r["failed_count"] = counts.get("Failed", 0)
        if r.send_kind == "Poll":
            label = label_lookup.get(r.poll_uuid)
            r["poll_label"] = (label.label or label.poll_text) if label else None

    return {"rows": rows, "has_more": has_more}


@frappe.whitelist()
def get_campaign_poll_results(batch_name):
    batch = frappe.db.get_value(SEND_BATCH_DOCTYPE, batch_name, ["send_kind", "poll_uuid", "total_groups"], as_dict=True)
    if not batch or batch.send_kind != "Poll":
        frappe.throw("This batch is not a Poll batch.")

    rows = frappe.db.sql(
        """
        SELECT ti.poll_choice AS choice, COUNT(*) AS cnt
        FROM "tabWA Group Turn Item" ti
        JOIN "tabWA Group Turn" t ON t.name = ti.parent
        WHERE t.related_campaign = %(batch)s
          AND ti.item_type = 'Poll Response'
        GROUP BY ti.poll_choice
        """,
        {"batch": batch_name}, as_dict=True,
    )

    option_counts = {}
    total_responses = 0
    for r in rows:
        total_responses += r.cnt
        if not r.choice:
            continue
        for choice in [c.strip() for c in r.choice.split(",") if c.strip()]:
            option_counts[choice] = option_counts.get(choice, 0) + r.cnt

    results = [{"option": k, "count": v} for k, v in sorted(option_counts.items(), key=lambda kv: -kv[1])]
    group_count = batch.total_groups or 0
    return {
        "results": results,
        "total_responses": total_responses,
        "group_count": group_count,
    }


@frappe.whitelist()
def get_all_polls_summary(date_from, date_to, wa_group=None, district=None, city=None, state=None,
                           school=None, start=0, page_length=25):
    start = max(int(start), 0)
    page_length = min(int(page_length), 100)

    date_from, date_to = _date_range_args(date_from, date_to)

    filters = {
        "geo": {"wa_group": wa_group, "district": district, "city": city, "state": state, "school": school},
    }
    conditions = ["b.send_kind = 'Poll'", "b.status = 'Sent'", "b.scheduled_send_at BETWEEN %(from)s AND %(to)s"]
    params = {"from": date_from, "to": date_to,
              "start": start, "page_length": page_length + 1}
    conditions, params = apply_geo_filters(conditions, params, filters, group_field="b.wa_group")

    batches = frappe.db.sql(
        f"""
        SELECT b.name, b.wa_group, b.poll_uuid, b.scheduled_send_at AS sent_at,
               b.total_groups AS group_count, b.is_multi_language_poll
        FROM "tabWA Send Batch" b
        WHERE {" AND ".join(conditions)}
        ORDER BY b.scheduled_send_at DESC
        LIMIT %(page_length)s OFFSET %(start)s
        """,
        params, as_dict=True,
    )
    has_more = len(batches) > page_length
    batches = batches[:page_length]
    if not batches:
        return {"rows": [], "has_more": False}

    names = [b.name for b in batches]

    response_counts_rows = frappe.db.sql(
        """
        SELECT t.related_campaign, COUNT(*) AS cnt
        FROM "tabWA Group Turn Item" ti
        JOIN "tabWA Group Turn" t ON t.name = ti.parent
        WHERE t.related_campaign IN %(names)s
          AND ti.item_type = 'Poll Response'
        GROUP BY t.related_campaign
        """,
        {"names": tuple(names)}, as_dict=True,
    )
    responses_by_batch = {r.related_campaign: r.cnt for r in response_counts_rows}

    staff_reply_counts = dict(frappe.db.sql(
        """
        SELECT t.related_campaign, COUNT(*)
        FROM "tabWA Send Message" sm
        JOIN "tabWA Group Turn" t ON t.name = sm.source_turn
        WHERE sm.origin = 'Direct Reply'
          AND t.related_campaign IN %(names)s
        GROUP BY t.related_campaign
        """,
        {"names": tuple(names)},
    ))

    group_names_map = {g.name: g.group_name for g in frappe.get_all(
        "WA Group", filters={"name": ["in", list({b.wa_group for b in batches if b.wa_group})]},
        fields=["name", "group_name"],
    )}

    from tap_lms.tap_lms.doctype.wa_poll_label.wa_poll_label import bulk_get_poll_labels
    label_lookup = bulk_get_poll_labels([b.poll_uuid for b in batches if b.poll_uuid])

    rows = []
    for b in batches:
        total_responses = responses_by_batch.get(b.name, 0)
        group_count = b.group_count or 1
        label_info = label_lookup.get(b.poll_uuid)
        label = (label_info.label or label_info.poll_text) if label_info else None
        rows.append({
            "campaign": b.name,
            "label": label or f"Poll sent on {b.sent_at} to {group_names_map.get(b.wa_group, b.wa_group) or 'target'}",
            "sent_at": b.sent_at,
            "wa_group_name": group_names_map.get(b.wa_group, b.wa_group),
            "groups_targeted": group_count,
            "is_multi_language_poll": bool(b.is_multi_language_poll),
            "total_responses": total_responses,
            "response_rate": round((total_responses / group_count) * 100, 1) if group_count else 0,
            "staff_replies": staff_reply_counts.get(b.name, 0),
        })

    return {"rows": rows, "has_more": has_more}


@frappe.whitelist()
def get_polls_overview(date_from, date_to, wa_group=None, district=None, city=None, state=None, school=None):
    data = get_all_polls_summary(date_from, date_to, wa_group, district, city, state, school,
                                  start=0, page_length=1000)
    rows = data["rows"]
    total_polls = len(rows)
    total_responses = sum(r["total_responses"] for r in rows)
    total_groups_targeted = sum(r["groups_targeted"] for r in rows)
    avg_response_rate = round(sum(r["response_rate"] for r in rows) / total_polls, 1) if total_polls else 0
    return {
        "total_polls": total_polls,
        "total_responses": total_responses,
        "total_groups_targeted": total_groups_targeted,
        "avg_response_rate": avg_response_rate,
    }


def _date_range_args(date_from, date_to):
    date_from_ts = date_from if " " in str(date_from) else f"{date_from} 00:00:00"
    date_to_ts = date_to if " " in str(date_to) else f"{date_to} 23:59:59"
    return date_from_ts, date_to_ts


def _rollup_geo_clause(district, city, state, wa_group, school=None):
    filters = {
        "geo": {"wa_group": wa_group, "district": district, "city": city, "state": state, "school": school},
        "include_disabled_groups": True,
    }
    conditions, params = apply_geo_filters([], {}, filters, group_field="wg.name")
    if not conditions:
        return "", {}
    return " AND " + " AND ".join(conditions), params


@frappe.whitelist()
def get_overview_summary(date_from, date_to, wa_group=None, district=None, city=None, state=None,
                          school=None, granularity="day"):
    date_from, date_to = _date_range_args(date_from, date_to)
    geo_clause, geo_params = _rollup_geo_clause(district, city, state, wa_group, school)
    rows = frappe.db.sql(
        f"""
        SELECT
            SUM(er.text_count + er.media_count + er.voice_count + er.poll_response_count +
                er.reaction_count + er.sticker_count) AS total_events,
            SUM(er.media_count) AS media_count,
            SUM(er.poll_response_count) AS poll_count,
            SUM(er.reaction_count) AS reaction_count,
            SUM(er.tagged_reply_count) AS tagged_reply_count,
            COUNT(DISTINCT er.wa_group) AS groups_active,
            SUM(er.ai_turns_drafted) AS ai_turns_drafted,
            SUM(er.ai_english_turns) AS ai_english_turns,
            SUM(er.ai_indic_turns) AS ai_indic_turns,
            SUM(er.ai_indic_fallback_turns) AS ai_indic_fallback_turns,
            SUM(er.ai_vision_calls) AS ai_vision_calls,
            SUM(er.ai_voice_calls) AS ai_voice_calls,
            SUM(er.ai_failed_turns) AS ai_failed_turns
        FROM "tabWA Event Rollup" er
        JOIN "tabWA Group" wg ON wg.name = er.wa_group
        WHERE er.bucket_datetime BETWEEN %(from)s AND %(to)s {geo_clause}
        """,
        {"from": date_from, "to": date_to, **geo_params}, as_dict=True,
    )
    summary = rows[0] if rows else {}

    media_summary = get_media_processing_summary(wa_group, district, city, state, school)
    summary["unprocessed_media"] = media_summary.get("unprocessed", 0)

    turn_rows = frappe.db.sql(
        """
        SELECT COUNT(*) FROM "tabWA Group Turn"
        WHERE turn_status = 'Ignored' AND last_item_at BETWEEN %(from)s AND %(to)s
        """,
        {"from": date_from, "to": date_to},
    )
    summary["ai_ignored_turns"] = turn_rows[0][0] if turn_rows else 0

    retry_queue_count = frappe.db.count(REACTION_RETRY_QUEUE_DOCTYPE, {"retry_attempts": ["<", 10]})
    summary["reactions_awaiting_group_match"] = retry_queue_count
    return summary


@frappe.whitelist()
def get_daily_trend(date_from, date_to, wa_group=None, district=None, city=None, state=None,
                     school=None, granularity="day"):
    date_from, date_to = _date_range_args(date_from, date_to)
    geo_clause, geo_params = _rollup_geo_clause(district, city, state, wa_group, school)
    trunc_unit = GRANULARITY_TRUNC.get(granularity, "day")
    return frappe.db.sql(
        f"""
        SELECT date_trunc('{trunc_unit}', er.bucket_datetime) AS bucket,
               SUM(er.text_count) AS text_count, SUM(er.media_count) AS media_count,
               SUM(er.voice_count) AS voice_count, SUM(er.poll_response_count) AS poll_response_count,
               SUM(er.reaction_count) AS reaction_count, SUM(er.sticker_count) AS sticker_count
        FROM "tabWA Event Rollup" er
        JOIN "tabWA Group" wg ON wg.name = er.wa_group
        WHERE er.bucket_datetime BETWEEN %(from)s AND %(to)s {geo_clause}
        GROUP BY bucket
        ORDER BY bucket ASC
        """,
        {"from": date_from, "to": date_to, **geo_params}, as_dict=True,
    )


@frappe.whitelist()
def get_top_active_groups(date_from, date_to, limit=5, wa_group=None, district=None, city=None, state=None, school=None):
    date_from, date_to = _date_range_args(date_from, date_to)
    limit = min(int(limit), 20)
    geo_clause, geo_params = _rollup_geo_clause(district, city, state, wa_group, school)
    return frappe.db.sql(
        f"""
        SELECT er.wa_group, wg.group_name, wg.district, wg.city, wg.state, wg.school
        FROM "tabWA Event Rollup" er
        JOIN "tabWA Group" wg ON wg.name = er.wa_group
        WHERE er.bucket_datetime BETWEEN %(from)s AND %(to)s {geo_clause}
        GROUP BY er.wa_group, wg.group_name, wg.district, wg.city, wg.state, wg.school
        LIMIT %(limit)s
        """,
        {"from": date_from, "to": date_to, "limit": limit, **geo_params}, as_dict=True,
    )


@frappe.whitelist()
def get_tag_distribution(date_from, date_to, wa_group=None, district=None, city=None, state=None, school=None):
    date_from, date_to = _date_range_args(date_from, date_to)
    filters = {"geo": {"wa_group": wa_group, "district": district, "city": city, "state": state, "school": school}}
    conditions = ["last_item_at BETWEEN %(from)s AND %(to)s", "ai_tags IS NOT NULL", "ai_tags != ''"]
    params = {"from": date_from, "to": date_to}
    conditions, params = apply_geo_filters(conditions, params, filters, group_field="wa_group")

    return frappe.db.sql(
        f"""
        SELECT tag, COUNT(*) AS count
        FROM (
            SELECT trim(unnest(string_to_array(ai_tags, ','))) AS tag
            FROM (
                SELECT ai_tags
                FROM "tabWA Group Turn"
                WHERE {" AND ".join(conditions)}
                ORDER BY last_item_at DESC
                LIMIT 20000
            ) capped
        ) tags
        WHERE tag != ''
        GROUP BY tag
        ORDER BY count DESC
        LIMIT 30
        """,
        params, as_dict=True,
    )


def _poll_only_exclusion_sql():
    return """
      EXISTS (
        SELECT 1 FROM "tabWA Group Turn Item" wgti
        WHERE wgti.parent = "tabWA Group Turn".name
          AND wgti.item_type != 'Poll Response'
      )
    """


@frappe.whitelist()
def get_conversations_summary(filters=None, wa_group=None, district=None, city=None, state=None, school=None,
                               tag=None, include_poll_only=False):
    filters = parse_filters(filters)
    include_poll_only = _to_bool(filters.get("include_poll_only", include_poll_only))
    if not filters.get("geo"):
        filters["geo"] = {"wa_group": wa_group, "district": district, "city": city, "state": state, "school": school}
    if tag and not filters.get("tag"):
        filters["tag"] = tag

    conditions, params = [], {}
    conditions, params = apply_geo_filters(conditions, params, filters)
    conditions, params = apply_date_range(conditions, params, filters, "last_item_at")
    conditions, params = apply_tag(conditions, params, filters)
    conditions, params = apply_ai_urgency(conditions, params, filters)
    if not include_poll_only:
        conditions.append(_poll_only_exclusion_sql())

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = frappe.db.sql(
        f"""
        SELECT turn_status, COUNT(*) AS cnt
        FROM "tabWA Group Turn"
        {where_clause}
        GROUP BY turn_status
        """,
        params, as_dict=True,
    )
    return {r.turn_status: r.cnt for r in rows}


@frappe.whitelist()
def get_conversation_turns(filters=None, turn_status=None, wa_group=None, tag=None, district=None, city=None,
                            state=None, school=None, start=0, page_length=25, include_poll_only=False):
    filters = parse_filters(filters)
    include_poll_only = _to_bool(filters.get("include_poll_only", include_poll_only))
    page_length = min(int(page_length), 100)
    start = max(int(start), 0)

    if not filters.get("geo"):
        filters["geo"] = {"wa_group": wa_group, "district": district, "city": city, "state": state, "school": school}
    if tag and not filters.get("tag"):
        filters["tag"] = tag
    if turn_status and not filters.get("turn_status"):
        if isinstance(turn_status, str) and turn_status.startswith("["):
            try:
                turn_status = json.loads(turn_status)
            except Exception:
                pass
        filters["turn_status"] = turn_status

    conditions, params = [], {"start": start, "page_length": page_length + 1}
    conditions, params = apply_geo_filters(conditions, params, filters)
    conditions, params = apply_date_range(conditions, params, filters, "last_item_at")
    conditions, params = apply_turn_status(conditions, params, filters)
    conditions, params = apply_tag(conditions, params, filters)
    conditions, params = apply_ai_urgency(conditions, params, filters)
    conditions, params = apply_contact_phone(conditions, params, filters)
    if not include_poll_only:
        conditions.append(_poll_only_exclusion_sql())

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = frappe.db.sql(
        f"""
        SELECT name, wa_group, contact_phone, item_count, last_item_at,
               is_closed, turn_status, ai_tags, ai_reply, ai_model_used, ai_urgency,
               ai_in_scope, related_campaign, scheduled_send_after,
               ai_attempt_count, ai_last_error
        FROM "tabWA Group Turn"
        {where_clause}
        ORDER BY last_item_at DESC
        LIMIT %(page_length)s OFFSET %(start)s
        """,
        params, as_dict=True,
    )

    has_more = len(rows) > page_length
    rows = rows[:page_length]

    items_by_turn = _bulk_turn_items_json([r.name for r in rows])

    from tap_lms.wagroupbot.inbound import bulk_resolve_contacts
    contact_map = bulk_resolve_contacts([r.contact_phone for r in rows])
    group_names_map = {g.name: g.group_name for g in frappe.get_all(
        "WA Group", filters={"name": ["in", list({r.wa_group for r in rows})]}, fields=["name", "group_name"]
    )} if rows else {}

    for r in rows:
        contact = contact_map.get(r.contact_phone) or {}
        r["contact_display"] = contact.get("display") or r.contact_phone
        r["contact_kind"] = contact.get("kind")
        r["wa_group_name"] = group_names_map.get(r.wa_group, r.wa_group)
        r["turn_items"] = items_by_turn.get(r.name, "[]")

    return {"rows": rows, "has_more": has_more}


@frappe.whitelist()
def get_conversation_groups(filters=None, start=0, page_length=25):
    filters = parse_filters(filters)
    page_length = min(int(page_length), 100)
    start = max(int(start), 0)

    conditions, params = [], {"start": start, "page_length": page_length + 1}
    conditions, params = apply_geo_filters(conditions, params, filters, group_field="t.wa_group")
    conditions, params = apply_date_range(conditions, params, filters, "t.last_item_at")
    conditions, params = apply_turn_status(conditions, params, filters, field="t.turn_status")
    conditions, params = apply_tag(conditions, params, filters, field="t.ai_tags")
    conditions, params = apply_ai_urgency(conditions, params, filters, field="t.ai_urgency")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = frappe.db.sql(
        f"""
        SELECT t.wa_group, wg.group_name,
               COUNT(*) FILTER (WHERE t.turn_status IN ('Open','Failed')) AS needs_attention,
               COUNT(*) AS turn_count,
               MAX(t.last_item_at) AS last_activity
        FROM "tabWA Group Turn" t
        JOIN "tabWA Group" wg ON wg.name = t.wa_group
        {where_clause}
        GROUP BY t.wa_group, wg.group_name
        ORDER BY last_activity DESC
        LIMIT %(page_length)s OFFSET %(start)s
        """,
        params, as_dict=True,
    )
    has_more = len(rows) > page_length
    return {"rows": rows[:page_length], "has_more": has_more}


@frappe.whitelist()
def get_group_timeline(wa_group, start=0, page_length=50, date_from=None, date_to=None):
    page_length = min(int(page_length), 200)
    start = max(int(start), 0)

    date_conditions = ""
    date_params = {}
    if date_from and date_to:
        date_from_ts, date_to_ts = _date_range_args(date_from, date_to)
        date_conditions = "AND ti.occurred_at BETWEEN %(date_from)s AND %(date_to)s"
        date_params = {"date_from": date_from_ts, "date_to": date_to_ts}

    total = frappe.db.sql(
        f"""
        SELECT COUNT(*) FROM "tabWA Group Turn Item" ti
        JOIN "tabWA Group Turn" t ON t.name = ti.parent
        WHERE t.wa_group = %(wa_group)s {date_conditions}
        """,
        {"wa_group": wa_group, **date_params},
    )[0][0]

    rows = frappe.db.sql(
        f"""
        SELECT ti.bq_id, ti.item_type, ti.body, ti.tagged_user_id, ti.media_gcs_url,
               ti.media_mime_type, ti.poll_choice, ti.transcript, ti.occurred_at,
               t.name AS turn_name, t.contact_phone, t.turn_status, t.ai_reply,
               t.related_campaign
        FROM "tabWA Group Turn Item" ti
        JOIN "tabWA Group Turn" t ON t.name = ti.parent
        WHERE t.wa_group = %(wa_group)s {date_conditions}
        ORDER BY ti.occurred_at DESC
        LIMIT %(page_length)s OFFSET %(start)s
        """,
        {"wa_group": wa_group, "page_length": page_length, "start": start, **date_params}, as_dict=True,
    )
    rows = list(reversed(rows))

    from tap_lms.wagroupbot.inbound import bulk_resolve_contacts
    contact_map = bulk_resolve_contacts([r.contact_phone for r in rows])

    for r in rows:
        contact = contact_map.get(r.contact_phone) or {}
        r["contact_display"] = contact.get("display") or r.contact_phone
        if hasattr(r.occurred_at, "isoformat"):
            r["occurred_at"] = r.occurred_at.isoformat()

    sent_rows = frappe.db.sql(
        f"""
        SELECT contact_phone, message_body, sent_at
        FROM "tabWA Send Message"
        WHERE wa_group = %(wa_group)s AND origin = 'Direct Reply' AND status = 'Sent'
        {date_conditions.replace('ti.occurred_at', 'sent_at')}
        ORDER BY sent_at DESC
        LIMIT %(page_length)s OFFSET %(start)s
        """,
        {"wa_group": wa_group, "page_length": page_length, "start": start, **date_params}, as_dict=True,
    )
    for r in sent_rows:
        if hasattr(r.sent_at, "isoformat"):
            r["sent_at"] = r.sent_at.isoformat()

    group_name = frappe.db.get_value("WA Group", wa_group, "group_name")

    return {
        "rows": rows,
        "replies": sent_rows,
        "has_more": (start + page_length) < total,
        "total": total,
        "group_name": group_name,
    }


@frappe.whitelist()
def get_conversations_gallery(filters=None, wa_group=None, district=None, city=None, state=None, school=None,
                               media_category=None, start=0, page_length=24):
    filters = parse_filters(filters)
    page_length = min(int(page_length), 100)
    start = max(int(start), 0)

    if not filters.get("geo"):
        filters["geo"] = {"wa_group": wa_group, "district": district, "city": city, "state": state, "school": school}
    if media_category and not filters.get("media_category"):
        filters["media_category"] = media_category

    conditions = ["ti.media_gcs_url IS NOT NULL", "ti.media_gcs_url != ''"]
    params = {"start": start, "page_length": page_length + 1}
    conditions, params = apply_geo_filters(conditions, params, filters, group_field="m.wa_group")
    conditions, params = apply_date_range(conditions, params, filters, "ti.occurred_at")

    unprocessed_only = filters.get("media_category") == "__unprocessed__"
    if unprocessed_only:
        conditions.append("m.is_processed = 0")
    else:
        conditions, params = apply_media_category(conditions, params, filters)

    where_clause = f"WHERE {' AND '.join(conditions)}"
    rows = frappe.db.sql(
        f"""
        SELECT m.name AS media_name, m.wa_group, m.source_turn, m.bq_id,
               ti.media_gcs_url, ti.media_mime_type, ti.body AS caption,
               ti.occurred_at, t.contact_phone,
               m.is_processed,
               COALESCE(m.category_override, m.ai_category) AS category,
               m.category_source,
               t.turn_status, t.ai_reply, t.ai_tags, t.related_campaign
        FROM "tabWA Media" m
        JOIN "tabWA Group Turn Item" ti ON ti.parent = m.source_turn AND ti.bq_id = m.bq_id
        LEFT JOIN "tabWA Group Turn" t ON t.name = m.source_turn
        {where_clause}
        ORDER BY ti.occurred_at DESC
        LIMIT %(page_length)s OFFSET %(start)s
        """,
        params, as_dict=True,
    )

    has_more = len(rows) > page_length
    rows = rows[:page_length]

    items_by_turn = _bulk_turn_items_json([r.source_turn for r in rows if r.source_turn])

    from tap_lms.wagroupbot.inbound import bulk_resolve_contacts
    contact_map = bulk_resolve_contacts([r.contact_phone for r in rows])
    group_names_map = {g.name: g.group_name for g in frappe.get_all(
        "WA Group", filters={"name": ["in", list({r.wa_group for r in rows if r.wa_group})]},
        fields=["name", "group_name"]
    )} if rows else {}

    for r in rows:
        contact = contact_map.get(r.contact_phone) or {}
        r["contact_display"] = contact.get("display") or r.contact_phone
        r["wa_group_name"] = group_names_map.get(r.wa_group, r.wa_group)
        r["poll_choice"] = None
        effective_caption = r.get("caption")
        items_json = items_by_turn.get(r.source_turn) if r.source_turn else None
        if items_json:
            try:
                items = json.loads(items_json)
                poll_item = next((it for it in items if it.get("item_type") == "Poll Response"), None)
                if poll_item:
                    r["poll_choice"] = poll_item.get("poll_choice")
                if not effective_caption:
                    media_idx = next((i for i, it in enumerate(items) if it.get("bq_id") == r.bq_id), None)
                    if media_idx is not None:
                        for neighbor in items[media_idx + 1:media_idx + 3]:
                            if neighbor.get("item_type") == "Text" and neighbor.get("body"):
                                effective_caption = neighbor["body"][:140]
                                break
            except Exception:
                pass
        r["caption"] = effective_caption

    return {"rows": rows, "has_more": has_more}


@frappe.whitelist()
def get_media_processing_summary(wa_group=None, district=None, city=None, state=None, school=None,
                                  date_from=None, date_to=None):
    filters = {"geo": {"wa_group": wa_group, "district": district, "city": city, "state": state, "school": school}}
    conditions, params = apply_geo_filters([], {}, filters, group_field="m.wa_group")
    if date_from and date_to:
        filters["date_range"] = {"from": date_from, "to": date_to}
        conditions, params = apply_date_range(conditions, params, filters, "ti.occurred_at")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    row = frappe.db.sql(
        f"""
        SELECT
            COUNT(*) FILTER (WHERE ti.media_mime_type = 'image') AS total_images,
            COUNT(*) FILTER (WHERE ti.media_mime_type = 'video') AS total_videos,
            COUNT(*) FILTER (WHERE ti.media_mime_type = 'sticker') AS total_stickers,
            COUNT(*) FILTER (WHERE m.is_processed = 1) AS processed,
            COUNT(*) FILTER (WHERE m.is_processed = 0) AS unprocessed
        FROM "tabWA Media" m
        JOIN "tabWA Group Turn Item" ti ON ti.parent = m.source_turn AND ti.bq_id = m.bq_id
        {where_clause}
        """,
        params, as_dict=True,
    )
    return row[0] if row else {}


@frappe.whitelist()
def get_media_category_summary(wa_group=None, district=None, city=None, state=None, school=None,
                                date_from=None, date_to=None):
    filters = {"geo": {"wa_group": wa_group, "district": district, "city": city, "state": state, "school": school}}
    conditions, params = apply_geo_filters([], {}, filters, group_field="m.wa_group")
    if date_from and date_to:
        filters["date_range"] = {"from": date_from, "to": date_to}
        conditions, params = apply_date_range(conditions, params, filters, "ti.occurred_at")
        join_clause = 'JOIN "tabWA Group Turn Item" ti ON ti.parent = m.source_turn AND ti.bq_id = m.bq_id'
    else:
        join_clause = ""
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    return frappe.db.sql(
        f"""
        SELECT COALESCE(category_override, ai_category, 'Uncategorized') AS category, COUNT(*) AS count
        FROM "tabWA Media" m
        {join_clause}
        {where_clause}
        GROUP BY category
        ORDER BY count DESC
        """,
        params, as_dict=True,
    )


@frappe.whitelist()
def get_media_ingestion_diagnostics(date_from, date_to, wa_group=None, district=None, city=None, state=None, school=None):
    date_from, date_to = _date_range_args(date_from, date_to)
    filters = {"geo": {"wa_group": wa_group, "district": district, "city": city, "state": state, "school": school}}

    conditions = ["t.last_item_at BETWEEN %(from)s AND %(to)s"]
    params = {"from": date_from, "to": date_to}
    conditions, params = apply_geo_filters(conditions, params, filters, group_field="t.wa_group")

    visual_item_count = frappe.db.sql(
        f"""
        SELECT COUNT(*)
        FROM "tabWA Group Turn Item" wgti
        JOIN "tabWA Group Turn" t ON t.name = wgti.parent
        WHERE {" AND ".join(conditions)}
          AND (
            wgti.item_type = 'Sticker'
            OR (wgti.item_type = 'Media' AND LOWER(COALESCE(wgti.media_mime_type, '')) IN ('image', 'sticker', 'video'))
          )
        """,
        params,
    )[0][0]

    media_conditions = ["ti.occurred_at BETWEEN %(from)s AND %(to)s"]
    media_params = {"from": date_from, "to": date_to}
    media_conditions, media_params = apply_geo_filters(media_conditions, media_params, filters, group_field="m.wa_group")

    media_count = frappe.db.sql(
        f"""
        SELECT COUNT(*)
        FROM "tabWA Media" m
        JOIN "tabWA Group Turn Item" ti ON ti.parent = m.source_turn AND ti.bq_id = m.bq_id
        WHERE {" AND ".join(media_conditions)}
        """,
        media_params,
    )[0][0]

    ffmpeg_available = bool(frappe.db.get_value(SETTINGS_DOCTYPE, None, "video_ffmpeg_available"))

    return {
        "turn_items_media_or_sticker": visual_item_count,
        "wa_media_rows": media_count,
        "ffmpeg_available": ffmpeg_available,
    }


@frappe.whitelist()
def set_media_category_override(media_name, category):
    frappe.only_for("System Manager")
    valid = set(MEDIA_CATEGORIES) | {""}
    if category not in valid:
        frappe.throw("Unknown category.")
    frappe.db.set_value(MEDIA_DOCTYPE, media_name, {
        "category_override": category or None,
        "category_source": "Manual" if category else "AI",
        "is_processed": 1 if category else frappe.db.get_value(MEDIA_DOCTYPE, media_name, "ai_category") and 1 or 0,
    })
    frappe.db.commit()
    return {"status": "ok"}


@frappe.whitelist()
def get_media_categories():
    return list(MEDIA_CATEGORIES)


@frappe.whitelist()
def get_reaction_retry_queue_summary():
    row = frappe.db.sql(
        """
        SELECT COUNT(*) AS cnt, MIN(inserted_at) AS oldest
        FROM "tabWA Reaction Retry Queue"
        WHERE retry_attempts < 10
        """,
        as_dict=True,
    )
    return row[0] if row else {"cnt": 0, "oldest": None}


@frappe.whitelist()
def list_reaction_retry_queue(start=0, page_length=25):
    start = max(int(start), 0)
    page_length = min(int(page_length), 100)
    rows = frappe.db.sql(
        """
        SELECT name, bq_uuid, wa_message_id, phone, reaction, body, inserted_at, retry_attempts
        FROM "tabWA Reaction Retry Queue"
        WHERE retry_attempts < 10
        ORDER BY inserted_at DESC
        LIMIT %(limit)s OFFSET %(start)s
        """,
        {"limit": page_length + 1, "start": start}, as_dict=True,
    )
    has_more = len(rows) > page_length
    return {"rows": rows[:page_length], "has_more": has_more}


@frappe.whitelist()
def retry_one_queued_reaction(name):
    frappe.only_for("System Manager")
    from tap_lms.wagroupbot.inbound import ingest_reaction
    row = frappe.db.get_value(
        REACTION_RETRY_QUEUE_DOCTYPE, name,
        ["bq_uuid", "wa_message_id", "phone", "reaction", "body", "inserted_at", "retry_attempts"], as_dict=True,
    )
    if not row:
        frappe.throw("Queued reaction not found.")

    settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
    ok, reason = ingest_reaction({
        "bq_uuid": row.bq_uuid, "wa_message_id": row.wa_message_id, "phone": row.phone,
        "reaction": row.reaction, "body": row.body, "inserted_at": row.inserted_at, "wa_group_id": None,
    }, settings)

    if ok:
        frappe.delete_doc(REACTION_RETRY_QUEUE_DOCTYPE, name, ignore_permissions=True)
    else:
        frappe.db.set_value(REACTION_RETRY_QUEUE_DOCTYPE, name, "retry_attempts", (row.retry_attempts or 0) + 1)
    frappe.db.commit()
    return {"status": "ok" if ok else "still_unresolved", "reason": reason}


@frappe.whitelist()
def get_safety_settings_summary():
    settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
    model_configs = [{
        "modality": row.modality,
        "enabled": bool(row.enabled),
        "provider": row.provider,
        "model_id": row.model_id,
        "api_base_url": row.api_base_url,
        "requests_per_minute": row.requests_per_minute,
        "daily_limit": row.daily_limit,
        "configured": bool(row.enabled and row.model_id and row.get_password("api_key", raise_exception=False)),
    } for row in (settings.ai_model_configs or [])]

    ignored_today = frappe.db.sql(
        """
        SELECT COUNT(*) FROM "tabWA Group Turn"
        WHERE turn_status = 'Ignored' AND last_item_at >= CURRENT_DATE
        """
    )[0][0]

    unreconciled_sends = frappe.db.sql(
        """
        SELECT COUNT(*) FROM "tabWA Send Message"
        WHERE status = 'Sent'
          AND origin IN ('Batch Wave', 'Direct Reply', 'Auto Reply Rule')
          AND (glific_message_id IS NULL OR glific_message_id = '')
          AND sent_at >= CURRENT_DATE - INTERVAL '7 days'
        """
    )[0][0]

    reaction_index_exists = bool(frappe.db.sql(
        """
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'tabWA Group Reaction' AND indexname = 'wa_group_reaction_unique_key'
        """
    ))

    retry_queue = get_reaction_retry_queue_summary()

    return {
        "ai_enabled": bool(settings.ai_enabled),
        "ai_mode_default": settings.ai_mode_default,
        "model_configs": model_configs,
        "ai_daily_draft_limit": settings.ai_daily_draft_limit,
        "ai_max_attempts": settings.ai_max_attempts,
        "content_safety_enabled": bool(settings.ai_content_safety_enabled),
        "pii_redaction_enabled": bool(settings.ai_pii_redaction_enabled),
        "blocked_categories": [c.strip() for c in (settings.ai_blocked_categories or "").split(",") if c.strip()],
        "support_routes_to_draft": bool(settings.ai_human_review_on_low_confidence),
        "natural_delay_enabled": bool(settings.natural_delay_enabled),
        "natural_delay_min_minutes": settings.natural_delay_min_minutes,
        "natural_delay_max_minutes": settings.natural_delay_max_minutes,
        "support_skip_delay": bool(settings.support_skip_delay),
        "media_auto_categorize_enabled": bool(settings.media_auto_categorize_enabled),
        "bq_max_bytes_billed": settings.bq_max_bytes_billed,
        "video_ai_mode": settings.video_ai_mode,
        "ignore_staff_numbers_enabled": bool(settings.ignore_staff_numbers_enabled),
        "ignored_staff_numbers": settings.ignored_staff_numbers,
        "my_tag_id": settings.my_tag_id,
        "my_tag_label": getattr(settings, "my_tag_label", None),
        "default_wave_size": settings.default_wave_size,
        "default_wave_gap_minutes": settings.default_wave_gap_minutes,
        "last_ai_draft_status": settings.last_ai_draft_status,
        "last_ai_draft_message": settings.last_ai_draft_message,
        "last_ai_draft_at": settings.last_ai_draft_at,
        "last_voice_transcribe_status": settings.last_voice_transcribe_status,
        "last_voice_transcribe_message": settings.last_voice_transcribe_message,
        "last_voice_transcribe_at": settings.last_voice_transcribe_at,
        "last_send_sweep_status": settings.last_send_sweep_status,
        "last_send_sweep_message": settings.last_send_sweep_message,
        "last_send_sweep_at": settings.last_send_sweep_at,
        "last_poll_status": settings.last_poll_status,
        "last_poll_message": settings.last_poll_message,
        "last_poll_at": settings.last_poll_at,
        "ignored_turns_today": ignored_today,
        "unreconciled_sends_last_7d": unreconciled_sends,
        "reaction_dedup_index_exists": reaction_index_exists,
        "reaction_retry_queue_size": retry_queue.get("cnt", 0),
        "reaction_retry_queue_oldest": retry_queue.get("oldest"),
    }


@frappe.whitelist()
def set_staff_filter_settings(ignore_staff_numbers_enabled=None, ignored_staff_numbers=None):
    frappe.only_for("System Manager")
    updates = {}
    if ignore_staff_numbers_enabled is not None:
        updates["ignore_staff_numbers_enabled"] = 1 if _to_bool(ignore_staff_numbers_enabled) else 0
    if ignored_staff_numbers is not None:
        updates["ignored_staff_numbers"] = ignored_staff_numbers
    if not updates:
        return {"status": "ok"}
    doc = frappe.get_doc(SETTINGS_DOCTYPE)
    doc.update(updates)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "ok"}


@frappe.whitelist()
def get_model_configs():
    settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
    return [{
        "name": row.name,
        "modality": row.modality,
        "enabled": bool(row.enabled),
        "provider": row.provider,
        "model_id": row.model_id,
        "api_base_url": row.api_base_url,
        "api_version": row.api_version,
        "requests_per_minute": row.requests_per_minute,
        "daily_limit": row.daily_limit,
        "notes": row.notes,
        "configured": bool(row.get_password("api_key", raise_exception=False)),
    } for row in (settings.ai_model_configs or [])]


@frappe.whitelist()
def set_model_config(modality, enabled=None, provider=None, model_id=None, api_key=None,
                      api_base_url=None, api_version=None, requests_per_minute=None, daily_limit=None):
    frappe.only_for("System Manager")
    settings = frappe.get_doc(SETTINGS_DOCTYPE)
    row = next((r for r in settings.ai_model_configs if r.modality == modality), None)
    if not row:
        row = settings.append("ai_model_configs", {"modality": modality})

    if enabled is not None:
        row.enabled = 1 if _to_bool(enabled) else 0
    if provider is not None:
        row.provider = provider
    if model_id is not None:
        row.model_id = model_id
    if api_key:
        row.api_key = api_key
    if api_base_url is not None:
        row.api_base_url = api_base_url
    if api_version is not None:
        row.api_version = api_version
    if requests_per_minute is not None:
        row.requests_per_minute = int(requests_per_minute)
    if daily_limit is not None:
        row.daily_limit = int(daily_limit)

    settings.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "ok"}


@frappe.whitelist()
def reset_system_prompt_to_default():
    frappe.only_for("System Manager")
    from tap_lms.wagroupbot.ai import TEXT_SYSTEM_PROMPT
    frappe.db.set_value(SETTINGS_DOCTYPE, None, "ai_system_prompt", TEXT_SYSTEM_PROMPT)
    frappe.db.commit()
    return {"status": "ok"}


@frappe.whitelist()
def get_modality_usage_today():
    frappe.only_for("System Manager")
    from frappe.utils import cint
    from tap_lms.wagroupbot.ai import _modality_daily_key, MODALITY_SLUGS
    cache = frappe.cache()
    return {m: cint(cache.get_value(_modality_daily_key(m)) or 0) for m in MODALITY_SLUGS}


@frappe.whitelist()
def upload_outbound_media(file_url):
    from tap_lms.wagroupbot.media_outbound import build_outbound_media_url, detect_media_type
    settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
    resolved_url = build_outbound_media_url(file_url, settings=settings)
    return {"url": resolved_url, "media_type": detect_media_type(file_url)}


@frappe.whitelist()
def get_turn_counts():
    rows = frappe.db.sql(
        f"""
        SELECT turn_status, COUNT(*) AS cnt FROM "tabWA Group Turn"
        WHERE {_poll_only_exclusion_sql()}
        GROUP BY turn_status
        """,
        as_dict=True,
    )
    return {r.turn_status: r.cnt for r in rows}


@frappe.whitelist()
def retry_failed_turn(turn_name):
    frappe.only_for("System Manager")
    current_status = frappe.db.get_value(TURN_DOCTYPE, turn_name, "turn_status")
    if current_status not in ("Failed", "Sending"):
        frappe.throw("Only a Failed (or stuck Sending) turn can be retried.")
    frappe.db.set_value(TURN_DOCTYPE, turn_name, {
        "turn_status": "Open",
        "ai_attempt_count": 0,
        "ai_last_error": "",
    })
    frappe.db.commit()
    from tap_lms.wagroupbot import ai
    ai.enqueue_turn_processing([turn_name])
    return {"status": "ok"}


@frappe.whitelist()
def approve_turn(turn_name, reply_text=None):
    frappe.only_for("System Manager")
    current_status = frappe.db.get_value(TURN_DOCTYPE, turn_name, "turn_status")
    if current_status != "Drafted":
        frappe.throw("Only a Drafted turn can be approved.")

    updates = {"turn_status": "Ready To Go"}
    if reply_text is not None:
        updates["ai_reply"] = reply_text
    frappe.db.set_value(TURN_DOCTYPE, turn_name, updates)
    frappe.db.commit()
    return {"status": "ok"}


@frappe.whitelist()
def update_turn_reply(turn_name, reply_text):
    frappe.only_for("System Manager")
    current_status = frappe.db.get_value(TURN_DOCTYPE, turn_name, "turn_status")
    if current_status not in ("Drafted", "Ready To Go"):
        frappe.throw("Only a Drafted or Ready To Go turn's reply can be edited.")
    frappe.db.set_value(TURN_DOCTYPE, turn_name, "ai_reply", reply_text)
    frappe.db.commit()
    return {"status": "ok"}


@frappe.whitelist()
def cancel_turn(turn_name):
    frappe.only_for("System Manager")
    current_status = frappe.db.get_value(TURN_DOCTYPE, turn_name, "turn_status")
    if current_status not in ("Drafted", "Ready To Go", "Failed"):
        frappe.throw("Only a Drafted, Ready To Go, or Failed turn can be discarded.")
    frappe.db.set_value(TURN_DOCTYPE, turn_name, "turn_status", "Discarded")
    frappe.db.commit()
    return {"status": "ok"}


@frappe.whitelist()
def send_manual_reply(turn_name, reply_text):
    frappe.only_for("System Manager")
    from tap_lms.wagroupbot.outbound import send_manual_reply as _send
    return _send(turn_name, reply_text, sent_by_user=frappe.session.user)


@frappe.whitelist()
def send_all_ready():
    frappe.only_for("System Manager")
    from tap_lms.wagroupbot.outbound import send_ready_turns
    return send_ready_turns()


@frappe.whitelist()
def get_turns_tagged_me(filters=None, wa_group=None, start=0, page_length=25):
    filters = parse_filters(filters)
    geo = filters.get("geo") or {}
    from tap_lms.wagroupbot.inbound import tagged_message_turns
    settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
    res = tagged_message_turns(
        wa_group=geo.get("wa_group") or wa_group,
        settings=settings,
        start=start,
        page_length=page_length,
    )

    rows = res["rows"]
    if rows:
        from tap_lms.wagroupbot.inbound import bulk_resolve_contacts
        contact_map = bulk_resolve_contacts([r["contact_phone"] for r in rows])
        group_names_map = {g.name: g.group_name for g in frappe.get_all(
            "WA Group", filters={"name": ["in", list({r["wa_group"] for r in rows})]},
            fields=["name", "group_name"],
        )}
        for r in rows:
            contact = contact_map.get(r["contact_phone"]) or {}
            r["contact_display"] = contact.get("display") or r["contact_phone"]
            r["wa_group_name"] = group_names_map.get(r["wa_group"], r["wa_group"])

    return res


@frappe.whitelist()
def get_turn_messages(turn_name):
    from tap_lms.wagroupbot.inbound import get_turn_items
    return get_turn_items(turn_name)


@frappe.whitelist()
def reactions_for_turn(turn_name):
    from tap_lms.wagroupbot.inbound import reactions_for_turn as _resolve
    return _resolve(turn_name)


@frappe.whitelist()
def get_reply_for_turn(turn_name):
    from tap_lms.wagroupbot.inbound import get_reply_for_turn as _resolve
    return _resolve(turn_name)


def _reactions_on_glific_message_id(glific_message_id, wa_group):
    if not glific_message_id:
        return []
    return frappe.get_all(
        REACTION_DOCTYPE,
        filters={"wa_group": wa_group, "reacted_message_bq_id": str(glific_message_id)},
        fields=["reaction_emoji", "contact_phone", "occurred_at"],
        order_by="occurred_at asc",
    )


@frappe.whitelist()
def reactions_for_campaign(batch_name):
    rows = frappe.get_all(
        SEND_MESSAGE_DOCTYPE, filters={"batch": batch_name, "origin": "Batch Wave", "status": "Sent"},
        fields=["wa_group", "glific_message_id"], limit_page_length=1,
    )
    if not rows:
        return []
    return _reactions_on_glific_message_id(rows[0].glific_message_id, rows[0].wa_group)


@frappe.whitelist()
def reactions_for_reply(reply_name):
    row = frappe.db.get_value(SEND_MESSAGE_DOCTYPE, reply_name, ["wa_group", "glific_message_id"], as_dict=True)
    if not row:
        return []
    return _reactions_on_glific_message_id(row.glific_message_id, row.wa_group)


@frappe.whitelist()
def get_reaction_emoji_breakdown(date_from, date_to, wa_group=None, district=None, city=None,
                                  state=None, school=None):
    from tap_lms.wagroupbot.inbound import reaction_emoji_breakdown

    if wa_group:
        is_enabled = frappe.db.get_value("WA Group", wa_group, "is_enabled")
        if not is_enabled:
            return []
        rows = reaction_emoji_breakdown(wa_group=wa_group, date_from=date_from, date_to=date_to, limit=50)
        return sorted(
            [{"reaction_emoji": r.emoji, "cnt": r.reaction_count} for r in rows],
            key=lambda x: -x["cnt"],
        )[:20]

    filters = {"geo": {"district": district, "city": city, "state": state, "school": school}}
    conditions, params = apply_geo_filters([], {}, filters, group_field="name")
    group_names = frappe.db.sql_list(
        f'SELECT name FROM "tabWA Group" WHERE {" AND ".join(conditions)}', params,
    )
    if not group_names:
        return []

    rows = reaction_emoji_breakdown(wa_group_names=group_names, date_from=date_from, date_to=date_to, limit=10000)
    merged = {}
    for r in rows:
        merged.setdefault(r.emoji, 0)
        merged[r.emoji] += r.reaction_count
    return sorted(
        [{"reaction_emoji": k, "cnt": v} for k, v in merged.items()],
        key=lambda x: -x["cnt"],
    )[:20]


@frappe.whitelist()
def get_reactions_feed(filters=None, wa_group=None, district=None, city=None, state=None, school=None,
                        start=0, page_length=25):
    filters = parse_filters(filters)
    page_length = min(int(page_length), 100)
    start = max(int(start), 0)

    if not filters.get("geo"):
        filters["geo"] = {"wa_group": wa_group, "district": district, "city": city, "state": state, "school": school}

    conditions, params = [], {}
    conditions, params = apply_geo_filters(conditions, params, filters)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    all_rows = frappe.db.sql(
        f"""
        SELECT wa_group, reacted_message_bq_id, reacted_message_body, reacted_message_media_url,
               reacted_message_type, reaction_emoji, contact_phone, occurred_at, reacted_on_our_message
        FROM "tabWA Group Reaction"
        {where_clause}
        ORDER BY occurred_at DESC
        LIMIT 5000
        """,
        params, as_dict=True,
    )

    grouped = {}
    order = []
    for r in all_rows:
        key = (r.wa_group, r.reacted_message_bq_id)
        if key not in grouped:
            grouped[key] = {
                "wa_group": r.wa_group,
                "reacted_message_bq_id": r.reacted_message_bq_id,
                "reacted_message_body": r.reacted_message_body,
                "reacted_message_media_url": r.reacted_message_media_url,
                "reacted_message_type": r.reacted_message_type,
                "reacted_on_our_message": bool(r.reacted_on_our_message),
                "reactions": [],
                "total_count": 0,
                "latest_at": r.occurred_at,
            }
            order.append(key)
        grouped[key]["reactions"].append({
            "emoji": r.reaction_emoji, "contact_phone": r.contact_phone, "occurred_at": r.occurred_at,
        })
        grouped[key]["total_count"] += 1
        if r.occurred_at > grouped[key]["latest_at"]:
            grouped[key]["latest_at"] = r.occurred_at

    ordered_keys = sorted(order, key=lambda k: grouped[k]["latest_at"], reverse=True)
    page_keys = ordered_keys[start:start + page_length]
    has_more = len(ordered_keys) > start + page_length

    rows = [grouped[k] for k in page_keys]
    contact_phones = [c["contact_phone"] for row in rows for c in row["reactions"]]
    from tap_lms.wagroupbot.inbound import bulk_resolve_contacts
    contact_map = bulk_resolve_contacts(contact_phones)
    group_names_map = {g.name: g.group_name for g in frappe.get_all(
        "WA Group", filters={"name": ["in", list({r["wa_group"] for r in rows})]}, fields=["name", "group_name"]
    )} if rows else {}

    for row in rows:
        row["wa_group_name"] = group_names_map.get(row["wa_group"], row["wa_group"])
        for c in row["reactions"]:
            contact = contact_map.get(c["contact_phone"]) or {}
            c["contact_display"] = contact.get("display") or c["contact_phone"]

    return {"rows": rows, "has_more": has_more}


@frappe.whitelist()
def get_model_usage_breakdown(date_from, date_to):
    date_from, date_to = _date_range_args(date_from, date_to)
    return frappe.db.sql(
        """
        SELECT ai_model_used, COUNT(*) AS turns
        FROM "tabWA Group Turn"
        WHERE turn_status IN ('Drafted', 'Ready To Go', 'Sent')
          AND ai_model_used IS NOT NULL AND ai_model_used != ''
          AND last_item_at BETWEEN %(from)s AND %(to)s
        GROUP BY ai_model_used
        ORDER BY turns DESC
        """,
        {"from": date_from, "to": date_to}, as_dict=True,
    )


@frappe.whitelist()
def get_wa_groups_for_filter(district=None, city=None, state=None, school=None, wa_group_collection=None,
                              include_disabled_groups=False):
    conditions = []
    params = {}
    if wa_group_collection:
        collection_groups = frappe.db.sql_list(
            'SELECT whatsapp_group FROM "tabWA Group Collection Mapping" WHERE collection = %(collection)s',
            {"collection": wa_group_collection},
        )
        if not collection_groups:
            return []
        conditions.append("name IN %(collection_groups)s")
        params["collection_groups"] = tuple(collection_groups)
    if district:
        conditions.append("district = %(district)s")
        params["district"] = district
    if city:
        conditions.append("city = %(city)s")
        params["city"] = city
    if state:
        conditions.append("state = %(state)s")
        params["state"] = state
    if school:
        conditions.append("school = %(school)s")
        params["school"] = school
    if not _to_bool(include_disabled_groups):
        conditions.append("is_enabled = 1")
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return frappe.db.sql(
        f"""
        SELECT name, group_name, school, district, city, state, group_language, is_enabled, sync_status
        FROM "tabWA Group"
        {where_clause}
        ORDER BY group_name ASC
        LIMIT 500
        """,
        params, as_dict=True,
    )


@frappe.whitelist()
def get_wa_group_collections():
    return frappe.get_all(
        "WA Group Collection",
        fields=["name", "collection_name", "group_count"],
        order_by="collection_name asc",
        limit_page_length=500,
    )


@frappe.whitelist()
def get_geo_options():
    return {
        "districts": frappe.get_all("WA Group", filters={"district": ["is", "set"]},
                                     pluck="district", distinct=True, order_by="district asc"),
        "cities": frappe.get_all("WA Group", filters={"city": ["is", "set"]},
                                  pluck="city", distinct=True, order_by="city asc"),
        "states": frappe.get_all("WA Group", filters={"state": ["is", "set"]},
                                  pluck="state", distinct=True, order_by="state asc"),
        "schools": frappe.get_all("School", fields=["name", "school_name"], limit_page_length=1000)
            if frappe.db.has_column("School", "school_name") else frappe.get_all("School", limit_page_length=1000),
    }


@frappe.whitelist()
def get_group_members(wa_group):
    return frappe.get_all(
        "WA Group Member",
        filters={"parent": wa_group, "parenttype": "WA Group"},
        fields=["member_type", "teacher", "student", "member_name", "phone_number", "school_id"],
        order_by="idx asc",
    )


@frappe.whitelist()
def refresh_group_members(wa_group):
    frappe.only_for("System Manager")
    from tap_lms.tap_lms.doctype.wa_group.wa_group import resync_group_members
    return resync_group_members(wa_group)


@frappe.whitelist()
def set_group_enabled(wa_group, is_enabled, disabled_reason=None):
    frappe.only_for("System Manager")
    frappe.db.set_value("WA Group", wa_group, {
        "is_enabled": 1 if _to_bool(is_enabled) else 0,
        "disabled_reason": disabled_reason if not _to_bool(is_enabled) else None,
    })
    frappe.db.commit()
    return {"status": "ok"}


@frappe.whitelist()
@glific_safe
def list_wa_polls():
    from tap_lms.wagroupbot.glific import GlificClient, list_wa_polls as _list
    return _list(GlificClient())


@frappe.whitelist()
@glific_safe
def sync_poll_labels():
    frappe.only_for("System Manager")
    from tap_lms.tap_lms.doctype.wa_poll_label.wa_poll_label import sync_poll_labels as _sync
    return _sync()


@frappe.whitelist()
@glific_safe
def create_poll(label, poll_text, options, allow_multiple_answer=False):
    frappe.only_for("System Manager")
    if isinstance(options, str):
        options = json.loads(options)
    if len(options) > 12:
        frappe.throw("Polls support a maximum of 12 options.")
    if len(poll_text) > 255:
        frappe.throw("Poll text must be 255 characters or fewer.")
    for opt in options:
        if len(opt) > 100:
            frappe.throw(f"Option '{opt[:30]}...' exceeds 100 characters.")

    allow_multiple_answer = _to_bool(allow_multiple_answer)

    from tap_lms.wagroupbot.glific import GlificClient, GlificTerminalError, _serialize_graphql_errors
    client = GlificClient()
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
            "pollContent": frappe.as_json({
                "text": poll_text,
                "options": [{"id": i, "name": o, "voters": [], "votes": 0} for i, o in enumerate(options)],
            }),
            "allowMultipleAnswer": allow_multiple_answer,
        }
    }
    result = client._graphql_request("CreateWaPoll", query, variables).get("createWaPoll") or {}
    errors = result.get("errors")
    if errors:
        raise GlificTerminalError(_serialize_graphql_errors(errors))
    poll = result.get("waPoll")
    if poll:
        from tap_lms.tap_lms.doctype.wa_poll_label.wa_poll_label import upsert_poll_label
        upsert_poll_label(poll.get("uuid"), poll.get("id"), poll.get("label"), poll_text, options)
    return poll


@frappe.whitelist()
def get_people_summary(date_from, date_to, filters=None, wa_group=None, district=None, city=None, state=None,
                        school=None, start=0, page_length=25, sort_by="messages"):
    filters = parse_filters(filters)
    date_from, date_to = _date_range_args(date_from, date_to)
    page_length = min(int(page_length), 100)
    start = max(int(start), 0)

    if not filters.get("geo"):
        filters["geo"] = {"wa_group": wa_group, "district": district, "city": city, "state": state, "school": school}

    conditions = ["t.last_item_at BETWEEN %(from)s AND %(to)s"]
    params = {"from": date_from, "to": date_to, "start": start, "page_length": page_length + 1}
    conditions, params = apply_geo_filters(conditions, params, filters, group_field="t.wa_group")

    sort_column = {
        "messages": "message_count",
        "last_seen": "last_seen",
        "replies": "replies_received",
    }.get(sort_by, "message_count")

    rows = frappe.db.sql(
        f"""
        SELECT
            t.contact_phone,
            COUNT(DISTINCT t.name) AS turn_count,
            SUM(t.item_count) AS message_count,
            MAX(t.last_item_at) AS last_seen,
            COUNT(DISTINCT t.wa_group) AS groups_touched,
            COUNT(DISTINCT CASE WHEN t.turn_status = 'Sent' THEN t.name END) AS replies_received,
            COUNT(DISTINCT CASE WHEN t.ai_urgency = 'Support' THEN t.name END) AS support_turns,
            COUNT(DISTINCT r.name) AS staff_tagged_replies
        FROM "tabWA Group Turn" t
        LEFT JOIN "tabWA Send Message" r ON r.origin = 'Direct Reply'
            AND r.contact_phone = t.contact_phone AND r.wa_group = t.wa_group
        WHERE {" AND ".join(conditions)}
        GROUP BY t.contact_phone
        ORDER BY {sort_column} DESC
        LIMIT %(page_length)s OFFSET %(start)s
        """,
        params, as_dict=True,
    )

    has_more = len(rows) > page_length
    rows = rows[:page_length]

    from tap_lms.wagroupbot.inbound import bulk_resolve_contacts
    contact_map = bulk_resolve_contacts([r.contact_phone for r in rows])
    for r in rows:
        contact = contact_map.get(r.contact_phone) or {}
        r["contact_display"] = contact.get("display") or r.contact_phone
        r["contact_kind"] = contact.get("kind")
        r["contact_name"] = contact.get("name")
        r["response_rate"] = round((r.replies_received / r.turn_count) * 100, 1) if r.turn_count else 0

    return {"rows": rows, "has_more": has_more}


@frappe.whitelist()
def get_person_turns(contact_phone, start=0, page_length=25):
    page_length = min(int(page_length), 100)
    start = max(int(start), 0)

    rows = frappe.db.sql(
        """
        SELECT name, wa_group, item_count, last_item_at, is_closed, turn_status,
               ai_tags, ai_reply, ai_model_used, ai_urgency, related_campaign, scheduled_send_after
        FROM "tabWA Group Turn"
        WHERE contact_phone = %(contact_phone)s
        ORDER BY last_item_at DESC
        LIMIT %(page_length)s OFFSET %(start)s
        """,
        {"contact_phone": contact_phone, "start": start, "page_length": page_length + 1}, as_dict=True,
    )
    has_more = len(rows) > page_length
    rows = rows[:page_length]

    items_by_turn = _bulk_turn_items_json([r.name for r in rows])

    group_names_map = {g.name: g.group_name for g in frappe.get_all(
        "WA Group", filters={"name": ["in", list({r.wa_group for r in rows})]}, fields=["name", "group_name"]
    )} if rows else {}

    replies_by_turn = {}
    if rows:
        oldest = min(r.last_item_at for r in rows)
        newest = max(r.last_item_at for r in rows)
        replies = frappe.get_all(
            SEND_MESSAGE_DOCTYPE,
            filters={
                "origin": "Direct Reply",
                "contact_phone": contact_phone,
                "sent_at": ["between", [oldest, newest]],
            },
            fields=["name", "wa_group", "message_body AS body_sent",
                     "sent_at", "source_turn"],
            order_by="sent_at asc",
        )
        for r in replies:
            if r.source_turn:
                replies_by_turn.setdefault(r.source_turn, []).append(r)

    for r in rows:
        r["wa_group_name"] = group_names_map.get(r.wa_group, r.wa_group)
        r["replies"] = replies_by_turn.get(r.name, [])
        r["turn_items"] = items_by_turn.get(r.name, "[]")

    return {"rows": rows, "has_more": has_more}


@frappe.whitelist()
def discard_all_turns(filters=None, turn_status=None, wa_group=None, tag=None, district=None, city=None,
                       state=None, school=None, include_poll_only=False):
    frappe.only_for("System Manager")
    filters = parse_filters(filters)
    include_poll_only = _to_bool(filters.get("include_poll_only", include_poll_only))

    if not filters.get("geo"):
        filters["geo"] = {"wa_group": wa_group, "district": district, "city": city, "state": state, "school": school}
    if tag and not filters.get("tag"):
        filters["tag"] = tag
    if turn_status and not filters.get("turn_status"):
        if isinstance(turn_status, str) and turn_status.startswith("["):
            try:
                turn_status = json.loads(turn_status)
            except Exception:
                pass
        filters["turn_status"] = turn_status
    elif not filters.get("turn_status"):
        filters["turn_status"] = ["Open", "Drafted"]

    conditions, params = [], {}
    conditions, params = apply_geo_filters(conditions, params, filters)
    conditions, params = apply_date_range(conditions, params, filters, "last_item_at")
    conditions, params = apply_turn_status(conditions, params, filters)
    conditions, params = apply_tag(conditions, params, filters)
    if not include_poll_only:
        conditions.append(_poll_only_exclusion_sql())

    conditions.append("turn_status NOT IN ('Sent', 'Discarded', 'Sending')")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    frappe.db.sql(
        f"""
        UPDATE "tabWA Group Turn"
        SET turn_status = 'Discarded', modified = now()
        {where_clause}
        """,
        params,
    )
    discarded = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
    frappe.db.commit()
    return {"discarded": discarded}