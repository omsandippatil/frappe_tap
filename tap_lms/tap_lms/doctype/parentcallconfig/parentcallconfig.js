// Copyright (c) 2026, Techt4dev and contributors
// For license information, please see license.txt

function parent_call_config_delete_prompt(name, on_success) {
	frappe.call({
		method: 'tap_lms.tap_lms.doctype.parentcallconfig.parentcallconfig.get_delete_references',
		args: { name: name },
		callback: function(r) {
			var refs = r.message || {};
			var lines = [
				__('This will permanently delete the script "{0}".', [name])
			];
			if (refs.voice_agent_default) {
				lines.push(__('• Clears it as the default on Voice Agent Settings.'));
			}
			if (refs.learning_units && refs.learning_units.length) {
				lines.push(
					__('• Removes it from {0} Learning Unit(s).', [refs.learning_units.length])
				);
			}
			lines.push(
				__('Tip: to keep the row but stop using it, uncheck <b>Is Active</b> instead.')
			);
			frappe.confirm(lines.join('<br>'), function() {
				frappe.call({
					method: 'tap_lms.tap_lms.doctype.parentcallconfig.parentcallconfig.delete_with_unlink',
					args: { name: name },
					freeze: true,
					freeze_message: __('Deleting script...'),
					callback: function(res) {
						if (res.message && res.message.success) {
							frappe.show_alert({ message: __('Script deleted'), indicator: 'green' });
							if (on_success) {
								on_success();
							}
						}
					}
				});
			});
		}
	});
}

frappe.ui.form.on('ParentCallConfig', {
	refresh: function(frm) {
		if (!frm.is_new() && frappe.model.can_delete('ParentCallConfig')) {
			frm.add_custom_button(__('Delete Script'), function() {
				parent_call_config_delete_prompt(frm.doc.name, function() {
					frappe.set_route('List', 'ParentCallConfig');
				});
			}, __('Actions'));
		}

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
