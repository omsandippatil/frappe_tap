import frappe
from frappe.model.document import Document
from frappe.utils import add_to_date, now_datetime

ORIGIN_ONLY_FIELDS = {
    "Batch Wave": {"batch", "wave_number"},
    "Direct Reply": {"contact_phone", "source_turn"},
    "Auto Reply Rule": {"contact_phone", "auto_reply_rule"},
    "External": {"external_sender_phone"},
}

ALL_ORIGIN_SPECIFIC_FIELDS = set().union(*ORIGIN_ONLY_FIELDS.values())

ORIGIN_REQUIRED_FIELDS = {
    "Batch Wave": {"batch", "wave_number"},
    "Direct Reply": {"contact_phone"},
    "Auto Reply Rule": {"contact_phone", "auto_reply_rule"},
    "External": {"external_sender_phone"},
}

# The partial unique index on (wa_group, glific_message_id) gives no
# protection in the window between a send and BQ-echo reconciliation, because
# glific_message_id is empty until the echo arrives — which can be a full
# poll cycle later. This guard catches the case the index structurally
# cannot: a duplicate Direct Reply / Auto Reply Rule row for the same
# group+contact+body landing within a short window (a retried job, a
# double-click that raced the UI's own disable-on-click). It does not and
# should not catch legitimate back-to-back identical messages sent minutes
# apart — RECONCILE_GUARD_SECONDS stays tight on purpose.
RECONCILE_GUARD_SECONDS = 10
GUARDED_ORIGINS = ("Direct Reply", "Auto Reply Rule")


class WASendMessage(Document):
    def validate(self):
        self._validate_origin_sparsity()
        self._validate_origin_required_fields()
        self._validate_error_field()
        if self.is_new():
            self._guard_against_unreconciled_duplicate()

    def _validate_origin_sparsity(self):
        allowed = ORIGIN_ONLY_FIELDS.get(self.origin, set())
        disallowed = ALL_ORIGIN_SPECIFIC_FIELDS - allowed
        for fieldname in disallowed:
            if self.get(fieldname):
                frappe.throw(f"{frappe.unscrub(fieldname)} must not be set when Origin is {self.origin}.")

    def _validate_origin_required_fields(self):
        required = ORIGIN_REQUIRED_FIELDS.get(self.origin, set())
        for fieldname in required:
            if not self.get(fieldname):
                frappe.throw(f"{frappe.unscrub(fieldname)} is required when Origin is {self.origin}.")

    def _validate_error_field(self):
        if self.status == "Sent" and self.error:
            frappe.throw("Error must be empty when Status is Sent.")
        if self.status == "Failed" and not self.error:
            frappe.throw("Error is required when Status is Failed.")

    def _guard_against_unreconciled_duplicate(self):
        if self.origin not in GUARDED_ORIGINS or self.status != "Sent":
            return
        if not self.wa_group or not self.contact_phone:
            return

        since = add_to_date(now_datetime(), seconds=-RECONCILE_GUARD_SECONDS)
        duplicate = frappe.db.exists(self.doctype, {
            "wa_group": self.wa_group,
            "contact_phone": self.contact_phone,
            "origin": self.origin,
            "message_body": self.message_body or "",
            "status": "Sent",
            "sent_at": [">=", since],
        })
        if duplicate:
            frappe.throw(
                f"A matching {self.origin} send to this contact in this group was already recorded "
                f"in the last {RECONCILE_GUARD_SECONDS} seconds — refusing what looks like a duplicate "
                f"send still waiting on BQ-echo reconciliation. If this is genuinely a second, distinct "
                f"message, wait a few seconds and retry."
            )


def on_doctype_update():
    frappe.db.add_index("WA Send Message", ["wa_group", "sent_at"])
    frappe.db.add_index("WA Send Message", ["origin", "status"])
    frappe.db.add_index("WA Send Message", ["batch", "wave_number"])
    frappe.db.add_index("WA Send Message", ["contact_phone", "sent_at"])
    frappe.db.add_index("WA Send Message", ["auto_reply_rule", "wa_group", "contact_phone", "sent_at"])
    frappe.db.add_index("WA Send Message", ["source_turn"])
    if not frappe.db.sql(
        """
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'tabWA Send Message' AND indexname = 'wa_send_message_glific_message_unique_key'
        """
    ):
        frappe.db.sql(
            """
            CREATE UNIQUE INDEX wa_send_message_glific_message_unique_key
            ON "tabWA Send Message" (wa_group, glific_message_id)
            WHERE glific_message_id IS NOT NULL AND glific_message_id != ''
            """
        )