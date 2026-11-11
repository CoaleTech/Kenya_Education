import frappe
from frappe import _

from frappe_education_kenya.parent_ops import PURPOSES, STAFF


def execute(filters=None):
	frappe.only_for(list(STAFF))
	frappe.has_permission("Guardian Consent", "report", throw=True)
	filters = filters or {}
	for key in filters:
		if key not in ("guardian", "student", "purpose", "status") or not isinstance(filters[key], str):
			frappe.throw(_("Invalid coverage filter."))
	purpose = filters.get("purpose")
	if purpose and purpose not in PURPOSES:
		frappe.throw(_("Invalid consent purpose."))
	if filters.get("status") and filters["status"] not in ("Granted", "Revoked", "Missing"):
		frappe.throw(_("Invalid consent status."))
	links = {"parenttype": "Student"}
	if filters.get("guardian"):
		links["guardian"] = filters["guardian"]
	if filters.get("student"):
		links["parent"] = filters["student"]
	pairs = sorted(
		{
			(r.guardian, r.parent)
			for r in frappe.get_all("Student Guardian", filters=links, fields=["guardian", "parent"])
			if r.guardian
		}
	)
	latest = {}
	if pairs:
		consent_filters = {
			"guardian": ["in", sorted({g for g, _s in pairs})],
			"student": ["in", sorted({s for _g, s in pairs})],
		}
		if purpose:
			consent_filters["purpose"] = purpose
		for row in frappe.get_all(
			"Guardian Consent",
			filters=consent_filters,
			fields=["name", "guardian", "student", "purpose", "status", "captured_on"],
			order_by="captured_on desc, creation desc, name desc",
		):
			latest.setdefault((row.guardian, row.student, row.purpose), row)
	data = []
	for guardian, student in pairs:
		for p in (purpose,) if purpose else PURPOSES:
			row = latest.get((guardian, student, p))
			status = row.status if row else "Missing"
			if filters.get("status") and filters["status"] != status:
				continue
			data.append(
				{
					"guardian": guardian,
					"student": student,
					"purpose": p,
					"status": status,
					"consent": row.name if row else None,
					"captured_on": row.captured_on if row else None,
				}
			)
	columns = [
		{
			"fieldname": "guardian",
			"label": _("Guardian"),
			"fieldtype": "Link",
			"options": "Guardian",
			"width": 180,
		},
		{
			"fieldname": "student",
			"label": _("Student"),
			"fieldtype": "Link",
			"options": "Student",
			"width": 180,
		},
		{"fieldname": "purpose", "label": _("Purpose"), "fieldtype": "Data", "width": 130},
		{"fieldname": "status", "label": _("Latest decision"), "fieldtype": "Data", "width": 130},
		{
			"fieldname": "consent",
			"label": _("Consent record"),
			"fieldtype": "Link",
			"options": "Guardian Consent",
			"width": 180,
		},
		{"fieldname": "captured_on", "label": _("Captured on"), "fieldtype": "Datetime", "width": 170},
	]
	return columns, data
