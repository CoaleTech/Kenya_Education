"""Make Education Settings the only home of the current academic year and term.

Education Kenya Settings used to carry its own copy. A value is carried over only where Education
Settings has none. The Kenya term dates were never read (Academic Term holds them) and are dropped
with the rest. Idempotent: once the Kenya values are gone there is nothing left to move.
"""

import frappe

# Kenya field -> (Education Settings field, Link target)
MOVED = {
	"current_academic_year": ("current_academic_year", "Academic Year"),
	"current_term": ("current_academic_term", "Academic Term"),
}
DROPPED = [*MOVED, "term_start_date", "term_end_date"]


def execute():
	education = frappe.get_single("Education Settings")
	changed = False
	for old, (new, doctype) in MOVED.items():
		value = frappe.db.get_single_value("Education Kenya Settings", old)
		if value and not education.get(new) and frappe.db.exists(doctype, value):
			education.set(new, value)
			changed = True
	if changed:
		education.save(ignore_permissions=True)
	frappe.db.delete("Singles", {"doctype": "Education Kenya Settings", "field": ["in", DROPPED]})
