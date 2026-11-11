import frappe
from frappe import _


def execute(filters=None):
	frappe.has_permission("Timetable Run", "report", throw=True)
	filters = filters or {}
	query = {}
	for key, target in (("run", "name"), ("academic_term", "academic_term")):
		if filters.get(key):
			if not isinstance(filters[key], str):
				frappe.throw(_("Invalid timetable filter"))
			query[target] = filters[key]
	runs = frappe.get_list(
		"Timetable Run",
		filters=query,
		fields=["name", "academic_term", "status"],
		limit_page_length=100,
		order_by="modified desc",
	)
	columns = [
		{
			"label": _("Run"),
			"fieldname": "run",
			"fieldtype": "Link",
			"options": "Timetable Run",
			"width": 180,
		},
		{
			"label": _("Academic Term"),
			"fieldname": "academic_term",
			"fieldtype": "Link",
			"options": "Academic Term",
			"width": 160,
		},
		{
			"label": _("Requirement"),
			"fieldname": "requirement",
			"fieldtype": "Link",
			"options": "Timetable Requirement",
			"width": 180,
		},
		{"label": _("Reason"), "fieldname": "reason", "fieldtype": "Data", "width": 480},
	]
	data = []
	if runs:
		by_run = {run.name: run for run in runs}
		for row in frappe.get_all(
			"Timetable Conflict",
			filters={
				"parent": ["in", list(by_run)],
				"parenttype": "Timetable Run",
				"parentfield": "conflicts",
			},
			fields=["parent", "requirement", "reason"],
			order_by="parent, idx",
		):
			data.append(
				{
					"run": row.parent,
					"academic_term": by_run[row.parent].academic_term,
					"requirement": row.requirement,
					"reason": row.reason,
				}
			)
	return (
		columns,
		data,
		_("Showing conflicts from the latest 100 accessible runs. Filter by run for an exact result."),
	)
