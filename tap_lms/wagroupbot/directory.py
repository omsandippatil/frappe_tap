import frappe
from frappe.utils import now_datetime

from tap_lms.wagroupbot.bq import run_query

SETTINGS_DOCTYPE = "WA Bot Settings"

GROUPS_COLUMNS = "id, label, wa_phone, last_communication_at"
COLLECTIONS_COLUMNS = "group_id, collection_id, group_label, collection_label"
GROUPS_PHONES_COLUMNS = "wa_group_id, wa_managed_phone_id, is_primary, is_active"


def pull_wa_groups_and_phones():
    settings = frappe.get_cached_doc(SETTINGS_DOCTYPE)
    try:
        groups = _query_wa_groups(settings)
        phones_synced = sum(1 for p in _derive_phones(groups) if _upsert_phone(p))
        frappe.db.commit()

        groups_synced = sum(1 for g in groups if _upsert_group(g))
        frappe.db.commit()

        phone_links = _query_wa_groups_phones(settings)
        links_synced = sum(1 for link in phone_links if _upsert_group_phone_link(link))
        frappe.db.commit()

        sync_status_updated = _refresh_sync_status_from_phone_links(phone_links)
        frappe.db.commit()

        collections = _query_wa_groups_collections(settings)
        collections_synced = sum(1 for c in collections if _upsert_collection(c))
        collection_mappings_synced = sum(1 for c in collections if _upsert_collection_mapping(c))
        frappe.db.commit()

        frappe.db.set_value(SETTINGS_DOCTYPE, None, {
            "last_sync_status": "Success",
            "last_sync_message": (
                f"Groups: {groups_synced}, Phones: {phones_synced}, "
                f"Group-Phone Links: {links_synced}, Sync Status Updated: {sync_status_updated}, "
                f"Collections: {collections_synced}, "
                f"Collection Mappings: {collection_mappings_synced}"
            ),
            "last_sync_at": now_datetime(),
        })
        frappe.db.commit()
        return {
            "groups": groups_synced,
            "phones": phones_synced,
            "group_phone_links": links_synced,
            "sync_status_updated": sync_status_updated,
            "collections": collections_synced,
            "collection_mappings": collection_mappings_synced,
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.db.set_value(SETTINGS_DOCTYPE, None, {
            "last_sync_status": "Failed",
            "last_sync_message": str(e),
            "last_sync_at": now_datetime(),
        })
        frappe.db.commit()
        frappe.log_error(title="WAGroupBot directory sync failed", message=frappe.get_traceback())
        return {"status": "error", "message": str(e)}


def _query_wa_groups(settings):
    sql = f"""
        SELECT {GROUPS_COLUMNS}
        FROM `{settings.bq_project}.{settings.bq_dataset}.wa_groups`
        QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) = 1
    """
    return run_query(sql, max_bytes_billed=settings.bq_max_bytes_billed)


def _query_wa_groups_phones(settings):
    sql = f"""
        SELECT {GROUPS_PHONES_COLUMNS}
        FROM `{settings.bq_project}.{settings.bq_dataset}.wa_groups_phones`
        WHERE is_active IS NOT FALSE
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY wa_group_id, wa_managed_phone_id ORDER BY updated_at DESC
        ) = 1
    """
    return run_query(sql, max_bytes_billed=settings.bq_max_bytes_billed)


def _query_wa_groups_collections(settings):
    sql = f"""
        SELECT {COLLECTIONS_COLUMNS}
        FROM `{settings.bq_project}.{settings.bq_dataset}.wa_groups_collections`
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY group_id, collection_id ORDER BY updated_at DESC
        ) = 1
    """
    return run_query(sql, max_bytes_billed=settings.bq_max_bytes_billed)


def _derive_phones(groups):
    seen = {}
    for g in groups:
        phone = g.get("wa_phone")
        if not phone or phone in seen:
            continue
        seen[phone] = {"phone": phone, "status": "active"}
    return list(seen.values())


def _upsert_phone(p):
    phone_number = p.get("phone")
    if not phone_number:
        return False
    is_active = 1 if (p.get("status") or "").lower() == "active" else 0

    existing = frappe.db.get_value(
        "WA Managed Phone", {"phone_number": phone_number},
        ["name", "is_active"], as_dict=True,
    )
    if existing:
        if existing.is_active == is_active:
            return False
        frappe.db.set_value("WA Managed Phone", existing.name, "is_active", is_active)
        return True

    doc = frappe.new_doc("WA Managed Phone")
    doc.phone_number = phone_number
    doc.label = phone_number
    doc.is_active = is_active
    doc.insert(ignore_permissions=True)
    return True


def _upsert_group(g):
    glific_id = str(g.get("id"))
    group_name = g.get("label")
    phone_number = g.get("wa_phone")
    last_communication_at = g.get("last_communication_at")
    phone_name = frappe.db.get_value("WA Managed Phone", {"phone_number": phone_number}, "name") if phone_number else None

    existing = frappe.db.get_value(
        "WA Group", {"glific_group_id": glific_id},
        ["name", "group_name", "wa_managed_phone", "last_message_at"], as_dict=True,
    )
    if existing:
        changed = (
            existing.group_name != group_name
            or existing.wa_managed_phone != phone_name
            or str(existing.last_message_at) != str(last_communication_at)
        )
        if not changed:
            return False
        frappe.db.set_value("WA Group", existing.name, {
            "group_name": group_name,
            "wa_managed_phone": phone_name,
            "last_message_at": last_communication_at,
        })
        return True

    doc = frappe.new_doc("WA Group")
    doc.glific_group_id = glific_id
    doc.group_name = group_name
    doc.wa_managed_phone = phone_name
    doc.last_message_at = last_communication_at
    doc.sync_status = "Unknown"
    doc.insert(ignore_permissions=True)
    return True


def _upsert_group_phone_link(link):
    wa_group = frappe.db.get_value("WA Group", {"glific_group_id": str(link.get("wa_group_id"))}, "name")
    if not wa_group or not link.get("is_primary"):
        return False

    phone_name = frappe.db.get_value(
        "WA Managed Phone", {"glific_phone_id": str(link.get("wa_managed_phone_id"))}, "name",
    )
    if not phone_name:
        return False

    current = frappe.db.get_value("WA Group", wa_group, "wa_managed_phone")
    if current == phone_name:
        return False
    frappe.db.set_value("WA Group", wa_group, "wa_managed_phone", phone_name)
    return True


def _refresh_sync_status_from_phone_links(phone_links):
    if not phone_links:
        return 0

    active_group_ids = {
        str(link.get("wa_group_id"))
        for link in phone_links
        if link.get("is_active") is not False
    }

    updated_count = 0

    if active_group_ids:
        frappe.db.sql(
            """
            UPDATE "tabWA Group"
            SET sync_status = 'Active', modified = now()
            WHERE glific_group_id IN %(ids)s
              AND sync_status != 'Active'
            """,
            {"ids": tuple(active_group_ids)},
        )
        updated_count += frappe.db.sql("SELECT ROW_COUNT()")[0][0]

    inactive_group_ids = {
        str(link.get("wa_group_id"))
        for link in phone_links
        if link.get("is_active") is False
    } - active_group_ids

    if inactive_group_ids:
        frappe.db.sql(
            """
            UPDATE "tabWA Group"
            SET sync_status = 'Inactive', modified = now()
            WHERE glific_group_id IN %(ids)s
              AND sync_status != 'Inactive'
            """,
            {"ids": tuple(inactive_group_ids)},
        )
        updated_count += frappe.db.sql("SELECT ROW_COUNT()")[0][0]

    return updated_count


def _upsert_collection(c):
    glific_id = str(c.get("collection_id"))
    collection_name = c.get("collection_label")

    existing = frappe.db.get_value(
        "WA Group Collection", {"glific_collection_id": glific_id},
        ["name", "collection_name"], as_dict=True,
    )
    if existing:
        if existing.collection_name == collection_name:
            return False
        frappe.db.set_value("WA Group Collection", existing.name, {
            "collection_name": collection_name,
            "last_synced_at": now_datetime(),
        })
        return True

    doc = frappe.new_doc("WA Group Collection")
    doc.glific_collection_id = glific_id
    doc.collection_name = collection_name
    doc.group_count = 0
    doc.last_synced_at = now_datetime()
    doc.insert(ignore_permissions=True)
    return True


def _upsert_collection_mapping(c):
    collection_name = frappe.db.get_value(
        "WA Group Collection", {"glific_collection_id": str(c.get("collection_id"))}, "name",
    )
    wa_group = frappe.db.get_value("WA Group", {"glific_group_id": str(c.get("group_id"))}, "name")
    if not collection_name or not wa_group:
        return False

    if frappe.db.exists("WA Group Collection Mapping", {
        "collection": collection_name, "whatsapp_group": wa_group,
    }):
        return False

    doc = frappe.new_doc("WA Group Collection Mapping")
    doc.collection = collection_name
    doc.whatsapp_group = wa_group
    doc.insert(ignore_permissions=True)
    return True