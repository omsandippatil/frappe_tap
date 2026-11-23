import frappe
from frappe.model.document import Document


class WAEventRollup(Document):
    pass


def on_doctype_update():
    frappe.db.add_index("WA Event Rollup", ["wa_group", "bucket_datetime"])
    frappe.db.add_index("WA Event Rollup", ["bucket_datetime"])