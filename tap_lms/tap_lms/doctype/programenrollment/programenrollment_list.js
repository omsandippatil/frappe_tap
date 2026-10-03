frappe.listview_settings['ProgramEnrollment'] = {
	onload: function(listview) {
		listview.page.add_inner_button(__('🏠 Voice AI Home'), function() {
			frappe.set_route('voice_ai_home');
		});

		listview.page.add_inner_button(__('📊 Analytics Dashboard'), function() {
			frappe.set_route('voice_campaign_dashboard');
		});
	}
};
