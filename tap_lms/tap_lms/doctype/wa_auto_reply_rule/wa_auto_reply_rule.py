import re

import frappe
from frappe.model.document import Document

MIME_PREFIX_TO_GLIFIC_TYPE = {
    "image": "image",
    "video": "video",
    "audio": "audio",
}


class WAAutoReplyRule(Document):
    def validate(self):
        if self.match_mode == "Regex" and self.trigger_keywords:
            try:
                re.compile(self.trigger_keywords)
            except re.error as e:
                frappe.throw(f"Invalid regex in Trigger Keywords: {e}")
        self._resolve_media_source()

    def _resolve_media_source(self):
        if self.response_type != "Media":
            return
        if self.response_media_file and self.response_media_url:
            self.response_media_url = None
        if not self.response_media_file and not self.response_media_url:
            frappe.throw("Either Response Media File or Response Media URL is required when Response Type is Media.")
        if self.response_media_file and not self.response_media_type:
            content_type = frappe.db.get_value("File", {"file_url": self.response_media_file}, "content_type") or ""
            prefix = content_type.split("/")[0].strip().lower()
            self.response_media_type = MIME_PREFIX_TO_GLIFIC_TYPE.get(prefix, "document")

    def on_update(self):
        from tap_lms.wagroupbot.outbound import invalidate_auto_reply_rules_cache
        invalidate_auto_reply_rules_cache()

    def on_trash(self):
        from tap_lms.wagroupbot.outbound import invalidate_auto_reply_rules_cache
        invalidate_auto_reply_rules_cache()