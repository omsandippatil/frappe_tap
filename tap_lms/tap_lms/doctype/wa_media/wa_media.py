import frappe
from frappe.model.document import Document


class WAMedia(Document):
    def validate(self):
        if self.category_override:
            self.category_source = "Manual"
        elif self.ai_category:
            self.category_source = "AI"
        self.is_processed = 1 if (self.category_override or self.ai_category) else 0

    def effective_category(self):
        return self.category_override or self.ai_category or None


def on_doctype_update():
    frappe.db.add_index("WA Media", ["wa_group", "is_processed"])


def upsert_media_record(wa_group, source_turn, bq_id):
    if not bq_id:
        return None

    existing = frappe.db.get_value("WA Media", {"bq_id": bq_id}, "name")
    if existing:
        return existing

    doc = frappe.new_doc("WA Media")
    doc.media_key = bq_id
    doc.wa_group = wa_group
    doc.source_turn = source_turn
    doc.bq_id = bq_id
    doc.insert(ignore_permissions=True)
    return doc.name


def set_ai_category(bq_id, category, confidence=None):
    if not bq_id or not category:
        return
    name = frappe.db.get_value("WA Media", {"bq_id": bq_id}, "name")
    if not name:
        return
    current_override = frappe.db.get_value("WA Media", name, "category_override")
    updates = {"ai_category": category, "is_processed": 1}
    if confidence:
        updates["ai_category_confidence"] = confidence
    if not current_override:
        updates["category_source"] = "AI"
    frappe.db.set_value("WA Media", name, updates)