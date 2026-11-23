import frappe
from frappe.model.document import Document


class WACampaignPollLanguage(Document):
    def validate(self):
        if not self.poll_label and self.language:
            self.poll_label = self.language