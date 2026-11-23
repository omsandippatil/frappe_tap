import json

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class WAPollLabel(Document):
    pass


def sync_poll_labels():
    from tap_lms.wagroupbot.glific import GlificClient, list_wa_polls as _list
    client = GlificClient()
    polls = _list(client)
    for p in polls:
        upsert_poll_label(p.get("uuid"), p.get("id"), p.get("label"))
    frappe.db.commit()
    return {"synced": len(polls)}


def upsert_poll_label(poll_uuid, glific_poll_id=None, label=None, poll_text=None, options=None):
    if not poll_uuid:
        return
    existing = frappe.db.exists("WA Poll Label", poll_uuid)
    updates = {"synced_at": now_datetime()}
    if glific_poll_id is not None:
        updates["glific_poll_id"] = str(glific_poll_id)
    if label is not None:
        updates["label"] = label
    if poll_text is not None:
        updates["poll_text"] = poll_text
    if options is not None:
        updates["options_json"] = json.dumps(options)

    if existing:
        frappe.db.set_value("WA Poll Label", existing, updates)
        return existing

    doc = frappe.new_doc("WA Poll Label")
    doc.poll_uuid = poll_uuid
    doc.update(updates)
    doc.insert(ignore_permissions=True)
    return doc.name


def get_poll_label(poll_uuid):
    if not poll_uuid:
        return None
    return frappe.db.get_value("WA Poll Label", poll_uuid, ["label", "poll_text"], as_dict=True)


def bulk_get_poll_labels(poll_uuids):
    poll_uuids = list({u for u in poll_uuids if u})
    if not poll_uuids:
        return {}
    rows = frappe.get_all(
        "WA Poll Label",
        filters={"poll_uuid": ["in", poll_uuids]},
        fields=["poll_uuid", "label", "poll_text"],
    )
    return {r.poll_uuid: r for r in rows}


def get_glific_poll_id(poll_uuid):
    if not poll_uuid:
        return None
    glific_poll_id = frappe.db.get_value("WA Poll Label", poll_uuid, "glific_poll_id")
    if glific_poll_id:
        return glific_poll_id

    from tap_lms.wagroupbot.glific import GlificClient, list_wa_polls as _list
    client = GlificClient()
    polls = _list(client)
    for p in polls:
        if p.get("uuid") == poll_uuid:
            upsert_poll_label(poll_uuid, p.get("id"), p.get("label"))
            return p.get("id")
    return None