import frappe
from frappe.model.document import Document

ITEM_TYPE_TO_FLAG = {
    "Text": "has_text",
    "Media": "has_media",
    "Voice": "has_voice",
    "Poll Response": "has_poll_response",
    "Reaction": "has_reaction",
    "Sticker": "has_sticker",
}


class WAGroupTurn(Document):
    def before_save(self):
        self.recompute_composition_flags()

    def recompute_composition_flags(self):
        present = {row.item_type for row in (self.turn_items or [])}
        for item_type, fieldname in ITEM_TYPE_TO_FLAG.items():
            self.set(fieldname, 1 if item_type in present else 0)
        self.item_count = len(self.turn_items or [])


def on_doctype_update():
    frappe.db.add_index("WA Group Turn", ["wa_group", "contact_phone", "is_closed", "last_item_at"])
    frappe.db.add_index("WA Group Turn", ["wa_group", "last_item_at"])
    frappe.db.add_index("WA Group Turn", ["wa_group", "turn_status", "last_item_at"])
    frappe.db.add_index("WA Group Turn", ["turn_status", "last_item_at"])
    frappe.db.add_index("WA Group Turn", ["turn_status", "ai_last_attempt_at"])