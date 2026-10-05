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

		if (frappe.model.can_delete('ParentCallConfig')) {
			listview.page.add_action_item(__('Delete selected (unlink refs)'), function() {
				var names = listview.get_checked_items(true);
				if (!names.length) {
					frappe.msgprint(__('Select at least one script.'));
					return;
				}
				frappe.confirm(
					__('Delete {0} script(s)? Linked Voice Settings / Learning Units will be updated.', [names.length]),
					function() {
						var pending = names.length;
						names.forEach(function(name) {
							frappe.call({
								method: 'tap_lms.tap_lms.doctype.parentcallconfig.parentcallconfig.delete_with_unlink',
								args: { name: name },
								callback: function() {
									pending -= 1;
									if (pending <= 0) {
										listview.refresh();
									}
								}
							});
						});
					}
				);
			});
		}
	}
};
