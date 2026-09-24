// Copyright (c) 2026, Techt4dev and contributors
// For license information, please see license.txt

frappe.ui.form.on('ParentCallConfig', {
	refresh: function(frm) {
		frm.add_custom_button(__('🧪 Test in Studio'), function() {
			frappe.set_route('vocallabs_test_call');
		});

		frm.add_custom_button(__('🏠 Voice AI Home'), function() {
			frappe.set_route('voice_ai_home');
		}, __('Navigation'));

		frm.add_custom_button(__('📊 Operations Dashboard'), function() {
			frappe.set_route('voice_campaign_dashboard');
		}, __('Navigation'));
	}
});
