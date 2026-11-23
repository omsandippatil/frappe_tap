import json
from collections import Counter

import frappe
import requests
from google.cloud import bigquery
from google.oauth2 import service_account

from tap_lms.wagroupbot.redis_lock import record_api_success

DAY_START = "2026-10-31 00:00:00"
DAY_END = "2026-11-01 00:00:00"


def _bq_client(settings):
    info = json.loads(settings.bq_credentials_json)
    credentials = service_account.Credentials.from_service_account_info(info)
    return bigquery.Client(project=settings.bq_project, credentials=credentials)


def _bq_query(client, settings, sql, max_bytes=None):
    job_config = bigquery.QueryJobConfig(
        maximum_bytes_billed=int(max_bytes or settings.bq_max_bytes_billed or 209715200)
    )
    return [dict(r.items()) for r in client.query(sql, job_config=job_config).result()]


def diagnose():
    record_api_success("bigquery")

    settings = frappe.get_cached_doc("WA Bot Settings")
    client = _bq_client(settings)
    project, dataset = settings.bq_project, settings.bq_dataset
    msg_table = settings.bq_table or "wa_messages"

    print("=" * 70)
    print("1. MESSAGES — BigQuery vs local, for 2026-10-31")
    print("=" * 70)

    bq_msgs = _bq_query(client, settings, f"""
        SELECT id, bq_uuid, type, contact_phone, wa_group_id, media_id, media_url, gcs_url,
               poll_content, inserted_at
        FROM `{project}.{dataset}.{msg_table}`
        WHERE inserted_at BETWEEN '{DAY_START}' AND '{DAY_END}'
        ORDER BY id ASC
    """)
    print(f"BigQuery rows for the day: {len(bq_msgs)}")

    bq_type_counts = Counter(r["type"] for r in bq_msgs)
    print(f"By type: {dict(bq_type_counts)}")

    bq_media_rows = [r for r in bq_msgs if r["type"] in ("image", "video", "document", "audio", "sticker")]
    bq_media_missing_gcs = [r for r in bq_media_rows if not r.get("gcs_url")]
    print(f"Media-type rows: {len(bq_media_rows)}, of which missing gcs_url upstream: {len(bq_media_missing_gcs)}")

    bq_ids = {r["id"] for r in bq_msgs}

    local_items = frappe.db.sql("""
        SELECT ti.parent AS turn_name, ti.bq_id, ti.item_type, ti.media_mime_type,
               ti.media_gcs_url, ti.occurred_at, t.wa_group, t.contact_phone
        FROM "tabWA Group Turn Item" ti
        JOIN "tabWA Group Turn" t ON t.name = ti.parent
        WHERE ti.occurred_at BETWEEN %(start)s AND %(end)s
        ORDER BY ti.occurred_at ASC
    """, {"start": DAY_START, "end": DAY_END}, as_dict=True)

    print(f"\nLocal Turn Items for the day: {len(local_items)}")
    local_type_counts = Counter(r.item_type for r in local_items)
    print(f"By type: {dict(local_type_counts)}")

    local_ids = {int(r.bq_id) for r in local_items if r.bq_id and r.bq_id.isdigit()}

    in_bq_not_local = bq_ids - local_ids
    in_local_not_bq = local_ids - bq_ids
    print(f"\nIn BigQuery but NOT ingested locally: {len(in_bq_not_local)} -> {sorted(in_bq_not_local)[:30]}")
    print(f"In local but NOT found in BigQuery:   {len(in_local_not_bq)} -> {sorted(in_local_not_bq)[:30]}")

    print("\nLocal media items still missing a GCS url:")
    local_media_missing = [r for r in local_items if r.item_type == "Media" and not r.media_gcs_url]
    for r in local_media_missing:
        bq_match = next((m for m in bq_msgs if str(m["id"]) == r.bq_id), None)
        print(f"  bq_id={r.bq_id} turn={r.turn_name} upstream_found={bool(bq_match)} "
              f"upstream_gcs_url={bq_match.get('gcs_url') if bq_match else 'N/A'}")

    print("\n" + "=" * 70)
    print("2. SIZE / REACHABILITY CHECK on gcs_url (HEAD request, capped at 30)")
    print("=" * 70)

    checked = 0
    for r in bq_media_rows:
        if checked >= 30:
            print("  ... capped at 30 checks, stopping")
            break
        url = r.get("gcs_url")
        if not url:
            continue
        checked += 1
        try:
            resp = requests.head(url, timeout=8, allow_redirects=True)
            size = resp.headers.get("Content-Length")
            print(f"  id={r['id']}  status={resp.status_code}  size={size or '?'} bytes  url={url}")
        except Exception as e:
            print(f"  id={r['id']}  HEAD FAILED: {e}  url={url}")

    print("\n" + "=" * 70)
    print("3. REACTIONS — BigQuery wa_reactions vs local, for 2026-10-31")
    print("=" * 70)

    reaction_sample = _bq_query(client, settings, f"SELECT * FROM `{project}.{dataset}.wa_reactions` LIMIT 1")
    print(f"wa_reactions columns: {list(reaction_sample[0].keys()) if reaction_sample else 'table appears empty'}")

    bq_reactions = []
    if reaction_sample:
        ts_col = next((c for c in ("inserted_at", "occurred_at", "created_at") if c in reaction_sample[0]), None)
        if ts_col:
            bq_reactions = _bq_query(client, settings, f"""
                SELECT * FROM `{project}.{dataset}.wa_reactions`
                WHERE {ts_col} BETWEEN '{DAY_START}' AND '{DAY_END}'
                ORDER BY {ts_col} ASC
            """)
            print(f"BigQuery reaction rows for the day: {len(bq_reactions)}")
        else:
            print(f"Couldn't find an obvious timestamp column, got: {list(reaction_sample[0].keys())}")

    local_reactions = frappe.db.sql("""
        SELECT bq_uuid, reacted_message_bq_id, contact_phone, reaction_emoji, occurred_at
        FROM "tabWA Group Reaction"
        WHERE occurred_at BETWEEN %(start)s AND %(end)s
    """, {"start": DAY_START, "end": DAY_END}, as_dict=True)
    print(f"Local WA Group Reaction rows for the day: {len(local_reactions)}")

    if bq_reactions:
        bq_reaction_uuids = {r.get("bq_uuid") for r in bq_reactions if r.get("bq_uuid")}
        local_reaction_uuids = {r.bq_uuid for r in local_reactions if r.bq_uuid}
        print(f"In BQ but not local: {len(bq_reaction_uuids - local_reaction_uuids)}")
        print(f"In local but not BQ: {len(local_reaction_uuids - bq_reaction_uuids)}")

    retry_queue_count = frappe.db.count("WA Reaction Retry Queue", {"retry_attempts": ["<", 10]})
    print(f"\nWA Reaction Retry Queue (unresolved): {retry_queue_count}")

    print("\n" + "=" * 70)
    print("4. POLLS — rows with non-empty poll_content, ANY date (none sent Oct 31)")
    print("=" * 70)

    bq_poll_rows = _bq_query(client, settings, f"""
        SELECT id, bq_uuid, type, contact_phone, wa_group_id, poll_content, inserted_at
        FROM `{project}.{dataset}.{msg_table}`
        WHERE poll_content IS NOT NULL AND poll_content != '{{}}' AND poll_content != ''
        ORDER BY inserted_at DESC
        LIMIT 20
    """)
    print(f"Rows upstream with non-empty poll_content (most recent 20): {len(bq_poll_rows)}")
    for r in bq_poll_rows:
        print(f"  id={r['id']} type={r['type']} phone={r['contact_phone']} "
              f"wa_group_id={r['wa_group_id']} inserted_at={r['inserted_at']}")
        print(f"    poll_content={r.get('poll_content')}")

    bq_poll_ids = {r["id"] for r in bq_poll_rows}
    local_poll_items = frappe.db.sql("""
        SELECT ti.parent AS turn_name, ti.bq_id, ti.item_type, ti.poll_choice, ti.occurred_at
        FROM "tabWA Group Turn Item" ti
        WHERE ti.item_type IN ('Poll Response', 'Poll Sent')
        ORDER BY ti.occurred_at DESC
        LIMIT 20
    """, as_dict=True)
    print(f"\nMost recent 20 local Poll Response/Poll Sent items (any date): {len(local_poll_items)}")
    for r in local_poll_items:
        found = int(r.bq_id) in bq_poll_ids if r.bq_id and r.bq_id.isdigit() else "N/A"
        print(f"  bq_id={r.bq_id} type={r.item_type} choice={r.poll_choice} at={r.occurred_at} found_upstream={found}")

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)