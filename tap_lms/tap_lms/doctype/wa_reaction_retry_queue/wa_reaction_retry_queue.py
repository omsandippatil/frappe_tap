import frappe
from frappe.model.document import Document

MAX_RETRY_ATTEMPTS = 10


class WAReactionRetryQueue(Document):
    pass


def on_doctype_update():
    frappe.db.add_index("WA Reaction Retry Queue", ["retry_attempts"])


def purge_exhausted():
    frappe.db.sql(
        'DELETE FROM "tabWA Reaction Retry Queue" WHERE retry_attempts >= %(max)s',
        {"max": MAX_RETRY_ATTEMPTS},
    )
    frappe.db.commit()