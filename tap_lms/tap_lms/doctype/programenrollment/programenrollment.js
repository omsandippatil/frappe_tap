// Copyright (c) 2026, Techt4dev and contributors
// For license information, please see license.txt

frappe.ui.form.on('ProgramEnrollment', {
	refresh: function(frm) {
		frm.add_custom_button(__('🏠 Voice AI Home'), function() {
			frappe.set_route('voice_ai_home');
		}, __('Voice AI'));

		frm.add_custom_button(__('📊 Operations Dashboard'), function() {
			frappe.set_route('voice_campaign_dashboard');
		}, __('Voice AI'));
	}
});
