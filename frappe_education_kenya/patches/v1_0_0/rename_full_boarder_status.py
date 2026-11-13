"""Rename the Student boarder status `Boarder (Full)` to `Boarder`.

The status names double as Student Category names (Day Scholar, Boarder, ...), so
enrollments can copy it. `create_custom_fields` never updates an existing Custom
Field, so the new options are applied here for sites that already have it.
"""

import frappe

OPTIONS = "\nDay Scholar\nBoarder\nQuarter Boarder\nWeekly Boarder"


def execute():
	if frappe.db.exists("Custom Field", "Student-kenya_boarder_status"):
		frappe.db.set_value("Custom Field", "Student-kenya_boarder_status", "options", OPTIONS)
	if frappe.db.has_column("Student", "kenya_boarder_status"):
		frappe.db.set_value(
			"Student",
			{"kenya_boarder_status": "Boarder (Full)"},
			"kenya_boarder_status",
			"Boarder",
			update_modified=False,
		)
	frappe.clear_cache(doctype="Student")
