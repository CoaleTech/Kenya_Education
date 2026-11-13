"""Pledge reminders and scheduled messages now live on the Communications tab of Education Settings.

Runs before the doctype sync, so the old fields are read straight from the Singles table.
Idempotent: once the old values are gone there is nothing left to move.
"""

import frappe

MOVED = {
	"pledge_reminder_days": "kenya_pledge_reminder_days",
	"enable_pledge_reminders": "kenya_enable_pledge_reminders",
	"enable_scheduled_messages": "kenya_enable_scheduled_messages",
}
OLD = "Education Kenya Settings"
NEW = "Education Settings"


def execute():
	singles = frappe.qb.DocType("Singles")
	rows = (
		frappe.qb.from_(singles)
		.select(singles.field, singles.value)
		.where(singles.doctype == OLD)
		.where(singles.field.isin(list(MOVED)))
		.run()
	)
	for field, value in rows:
		frappe.db.set_single_value(NEW, MOVED[field], value, update_modified=False)
	frappe.db.delete("Singles", {"doctype": OLD, "field": ["in", list(MOVED)]})
