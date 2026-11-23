import frappe
from frappe.model.document import Document

STATUS_TRANSITIONS = {
    "Draft": {"Scheduled", "Cancelled"},
    "Scheduled": {"Throttling", "Sent", "Partially Failed", "Failed", "Cancelled", "Draft"},
    "Throttling": {"Sent", "Partially Failed", "Failed", "Cancelled"},
    "Sent": set(),
    "Partially Failed": set(),
    "Failed": {"Scheduled"},
    "Cancelled": set(),
}

DEFAULT_POLL_RESPONSE_WINDOW_HOURS = 4


class WASendBatch(Document):
    def validate(self):
        self._validate_target()
        self._validate_content()
        self._validate_wave_settings()
        self._validate_status_transition()
        self._set_title()

    def _validate_target(self):
        if self.target_type == "Group" and not self.wa_group:
            frappe.throw("WA Group is required when Target Type is Group.")
        if self.target_type == "Collection" and not self.wa_group_collection:
            frappe.throw("WA Group Collection is required when Target Type is Collection.")
        if self.target_type == "Geo" and not (self.district or self.city or self.state or self.school):
            frappe.throw("At least one of District, City, State or School is required when Target Type is Geo.")

    def _validate_content(self):
        if self.send_kind == "Flow" and not self.glific_flow_id:
            frappe.throw("Glific Flow ID is required when Send Kind is Flow.")
        if self.send_kind == "Poll":
            if self.is_multi_language_poll:
                if not self.poll_languages:
                    frappe.throw("At least one Poll Language Variant row is required for a multi-language poll.")
                if not any(r.is_default for r in self.poll_languages):
                    frappe.throw("One Poll Language Variant row must be marked Default.")
            elif not self.poll_uuid:
                frappe.throw("Poll UUID is required when Send Kind is Poll.")
            if self.poll_response_window_hours in (None, ""):
                self.poll_response_window_hours = DEFAULT_POLL_RESPONSE_WINDOW_HOURS
            else:
                self.poll_response_window_hours = frappe.utils.cint(self.poll_response_window_hours)
            if self.poll_response_window_hours <= 0:
                frappe.throw("Poll Response Window Hours must be greater than 0.")
        if self.send_kind == "Media":
            if self.media_file and self.media_url:
                self.media_url = None
            if not self.media_file and not self.media_url:
                frappe.throw("Either Media File or Media URL is required when Send Kind is Media.")

    def _validate_wave_settings(self):
        settings = frappe.get_cached_doc("WA Bot Settings")

        if self.wave_size in (None, ""):
            self.wave_size = settings.default_wave_size or 25
        else:
            self.wave_size = frappe.utils.cint(self.wave_size)

        if self.wave_gap_minutes in (None, ""):
            self.wave_gap_minutes = settings.default_wave_gap_minutes if settings.default_wave_gap_minutes is not None else 10
        else:
            self.wave_gap_minutes = frappe.utils.cint(self.wave_gap_minutes)

        if self.wave_size <= 0:
            frappe.throw("Wave Size must be greater than 0.")
        if self.wave_gap_minutes < 0:
            frappe.throw("Wave Gap Minutes cannot be negative.")

    def _validate_status_transition(self):
        if self.is_new():
            return
        previous_status = frappe.db.get_value("WA Send Batch", self.name, "status")
        if previous_status and previous_status != self.status:
            allowed = STATUS_TRANSITIONS.get(previous_status, set())
            if self.status not in allowed:
                frappe.throw(f"Cannot move a {previous_status} send from {previous_status} to {self.status}.")
        if previous_status == "Draft" and self.status == "Draft":
            if self.resolved_target_groups:
                frappe.throw("A Draft batch must not carry a resolved target list. Call expand_send_batch only when scheduling.")

    def _set_title(self):
        if self.title:
            return
        target_label = self.wa_group or self.wa_group_collection or self.district or self.city or self.state or self.school or "target"
        self.title = f"{self.send_kind} to {target_label} — {frappe.utils.now_datetime().strftime('%Y-%m-%d %H:%M')}"


def on_doctype_update():
    frappe.db.add_index("WA Send Batch", ["status", "next_wave_at"])
    frappe.db.add_index("WA Send Batch", ["target_type"])