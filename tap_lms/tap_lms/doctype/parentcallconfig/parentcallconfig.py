# Copyright (c) 2026, Techt4dev and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ParentCallConfig(Document):
	pass


def _collect_references(name):
	"""Where this ParentCallConfig is still referenced (blocks normal Frappe delete)."""
	refs = {
		"voice_agent_default": False,
		"learning_units": [],
	}

	if frappe.db.exists("VoiceAgentSettings", "VoiceAgentSettings"):
		default = frappe.db.get_single_value(
			"VoiceAgentSettings", "default_parent_call_config"
		)
		if default == name:
			refs["voice_agent_default"] = True

	rows = frappe.get_all(
		"UnitContentItem",
		filters={"content_type": "ParentCallConfig", "content": name},
		fields=["parent"],
		distinct=True,
	)
	refs["learning_units"] = [r.parent for r in rows if r.parent]
	return refs


def _unlink_references(name):
	"""Clear links so ParentCallConfig can be removed without orphaning curriculum."""
	if frappe.db.exists("VoiceAgentSettings", "VoiceAgentSettings"):
		settings = frappe.get_single("VoiceAgentSettings")
		if settings.default_parent_call_config == name:
			settings.default_parent_call_config = ""
			settings.save(ignore_permissions=True)

	for row in frappe.get_all(
		"UnitContentItem",
		filters={"content_type": "ParentCallConfig", "content": name},
		fields=["parent"],
	):
		parent_name = row.parent
		if not parent_name or not frappe.db.exists("LearningUnit", parent_name):
			continue
		lu = frappe.get_doc("LearningUnit", parent_name)
		lu.content_items = [
			item
			for item in (lu.content_items or [])
			if not (
				item.content_type == "ParentCallConfig" and item.content == name
			)
		]
		lu.save(ignore_permissions=True)


@frappe.whitelist()
def get_delete_references(name):
	"""Return what still points at this script (for UI before delete)."""
	if not name or not frappe.db.exists("ParentCallConfig", name):
		frappe.throw(_("Parent Call Config not found."))
	frappe.has_permission("ParentCallConfig", "delete", throw=True)
	return _collect_references(name)


@frappe.whitelist()
def delete_with_unlink(name):
	"""
	Remove a ParentCallConfig after clearing VoiceAgentSettings + LearningUnit links.

	Standard Desk delete often fails with LinkExistsError because scripts are
	referenced from VoiceAgentSettings.default_parent_call_config and from
	UnitContentItem rows on LearningUnit.
	"""
	if not name or not frappe.db.exists("ParentCallConfig", name):
		frappe.throw(_("Parent Call Config not found."))

	frappe.has_permission("ParentCallConfig", "delete", throw=True)

	_unlink_references(name)
	frappe.delete_doc("ParentCallConfig", name, force=1)
	frappe.db.commit()
	return {"success": True, "deleted": name}


@frappe.whitelist()
def delete_all_scripts():
	"""Delete every ParentCallConfig (clears VoiceAgentSettings + LU links first)."""
	frappe.only_for("System Manager")
	names = frappe.get_all("ParentCallConfig", pluck="name")
	deleted = []
	for name in names:
		delete_with_unlink(name)
		deleted.append(name)
	return {"success": True, "deleted_count": len(deleted), "deleted": deleted}
