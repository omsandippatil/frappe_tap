// Copyright (c) 2026, Techt4dev and contributors
// For license information, please see license.txt

frappe.ui.form.on('VoiceAgentSettings', {
	refresh: function(frm) {
		frm.add_custom_button(__('🏠 Voice AI Home'), function() {
			frappe.set_route('voice_ai_home');
		});

		frm.add_custom_button(__('📊 Analytics Dashboard'), function() {
			frappe.set_route('voice_campaign_dashboard');
		});

		frm.add_custom_button(__('🧪 Testing Studio'), function() {
			frappe.set_route('vocallabs_test_call');
		});
	}
});
