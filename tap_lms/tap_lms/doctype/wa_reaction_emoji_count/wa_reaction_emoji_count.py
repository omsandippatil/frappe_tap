import frappe
from frappe.model.document import Document


class WAReactionEmojiCount(Document):
    pass


def on_doctype_update():
    frappe.db.add_index("WA Reaction Emoji Count", ["wa_group", "reaction_count"])