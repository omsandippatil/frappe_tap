import tap_lms.imgana.submission as m
a = m.get_assignment_context(assignment_id="SC_L4_CA1-Basic")
print(a)


assignment_id="SC_L4_CA1-Basic"
assignment = frappe.get_doc("Assignment", assignment_id)
print(assignment.as_dict())