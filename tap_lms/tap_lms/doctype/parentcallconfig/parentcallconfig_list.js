frappe.listview_settings['ParentCallConfig'] = {
	onload: function(listview) {
		listview.page.add_inner_button(__('🏠 Voice AI Home'), function() {
			frappe.set_route('voice_ai_home');
		});

		listview.page.add_inner_button(__('📊 Analytics Dashboard'), function() {
			frappe.set_route('voice_campaign_dashboard');
		});

		listview.page.add_inner_button(__('🧪 Testing Studio'), function() {
			frappe.set_route('vocallabs_test_call');
		});
	}
};
