import frappe
from frappe.model.document import Document


class WAMediaToken(Document):
    pass


def on_doctype_update():
    frappe.db.add_index("WA Media Token", ["expires_at"])


def purge_expired():
    frappe.db.sql(
        'DELETE FROM "tabWA Media Token" WHERE expires_at < %(now)s',
        {"now": frappe.utils.now_datetime()},
    )
    frappe.db.commit()