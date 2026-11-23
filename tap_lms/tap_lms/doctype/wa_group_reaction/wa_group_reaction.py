import frappe
from frappe.model.document import Document


class WAGroupReaction(Document):
    pass


def on_doctype_update():
    frappe.db.add_index("WA Group Reaction", ["wa_group", "occurred_at"])
    frappe.db.add_index("WA Group Reaction", ["normalized_emoji"])
    frappe.db.sql(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS wa_group_reaction_unique_key
        ON "tabWA Group Reaction" (wa_group, reacted_message_bq_id, contact_phone)
        """
    )