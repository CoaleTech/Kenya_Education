"""Per-year capacity and placement totals, without protected KJSEA data."""

import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.utils import cint

from frappe_education_kenya.pathways import COMBINATION, current_academic_year


def execute(filters=None):
	frappe.only_for(["Academic Admin", "Head Teacher", "Instructor"])
	frappe.has_permission(COMBINATION, "report", throw=True)
	filters = frappe._dict(filters or {})
	for key in ("academic_year", "pathway", "track", "combination"):
		if filters.get(key) is not None and not isinstance(filters[key], str):
			frappe.throw(_("Report filters must be names, not filter expressions."))
	year = filters.academic_year or current_academic_year()
	combination = frappe.qb.DocType(COMBINATION)
	choice = frappe.qb.DocType("Student Pathway Choice")
	query = (
		frappe.qb.from_(combination)
		.left_join(choice)
		.on(
			(choice.placement == combination.name)
			& (choice.academic_year == year)
			& (choice.workflow_state == "Placed")
		)
		.select(
			combination.name.as_("combination"),
			combination.pathway,
			combination.track,
			combination.capacity,
			combination.enabled,
			Count(choice.name).as_("placed"),
		)
		.groupby(
			combination.name,
			combination.pathway,
			combination.track,
			combination.capacity,
			combination.enabled,
		)
		.orderby(combination.pathway, combination.track, combination.name)
	)
	for key, column in (
		("pathway", combination.pathway),
		("track", combination.track),
		("combination", combination.name),
	):
		if filters.get(key):
			query = query.where(column == filters[key])
	data = query.run(as_dict=True)
	for row in data:
		row.academic_year = year
		row.remaining = max(0, cint(row.capacity) - cint(row.placed))
		row.over_capacity = max(0, cint(row.placed) - cint(row.capacity))
	columns = [
		{
			"label": _("Academic Year"),
			"fieldname": "academic_year",
			"fieldtype": "Link",
			"options": "Academic Year",
			"width": 125,
		},
		{
			"label": _("Combination"),
			"fieldname": "combination",
			"fieldtype": "Link",
			"options": COMBINATION,
			"width": 220,
		},
		{
			"label": _("Pathway"),
			"fieldname": "pathway",
			"fieldtype": "Link",
			"options": "CBC Pathway",
			"width": 150,
		},
		{"label": _("Track"), "fieldname": "track", "fieldtype": "Data", "width": 190},
		{"label": _("Available"), "fieldname": "enabled", "fieldtype": "Check", "width": 95},
		{"label": _("Capacity"), "fieldname": "capacity", "fieldtype": "Int", "width": 100},
		{"label": _("Placed"), "fieldname": "placed", "fieldtype": "Int", "width": 90},
		{"label": _("Remaining"), "fieldname": "remaining", "fieldtype": "Int", "width": 100},
		{"label": _("Over Capacity"), "fieldname": "over_capacity", "fieldtype": "Int", "width": 120},
	]
	return columns, data
