"""Outstanding overdue copies, optionally including recorded unpaid employee/student fines."""

import frappe
from frappe import _
from frappe.utils import cint, date_diff, getdate, today

from frappe_education_kenya.library import STAFF_READ_ROLES, calculate_fine


def execute(filters=None):
	frappe.only_for(list(STAFF_READ_ROLES))
	frappe.has_permission("Library Circulation", "report", throw=True)
	filters = frappe._dict(filters or {})
	as_of = getdate(filters.as_of or today())
	loan, copy = frappe.qb.DocType("Library Circulation"), frappe.qb.DocType("Library Copy")
	condition = (loan.status == "Issued") & (loan.due_on < as_of)
	if cint(filters.include_returned_with_fines):
		condition |= (loan.status == "Returned") & (loan.fine_amount > 0)
	query = (
		frappe.qb.from_(loan)
		.join(copy)
		.on(copy.name == loan.copy)
		.select(
			loan.name,
			loan.copy,
			copy.barcode,
			copy.article,
			loan.borrower_type,
			loan.borrower,
			loan.issued_on,
			loan.due_on,
			loan.returned_on,
			loan.status,
			loan.fine_amount,
			loan.fine_status,
			loan.currency,
		)
		.where(condition)
	)
	if filters.borrower_type:
		if filters.borrower_type not in ("Student", "Employee"):
			frappe.throw(_("Invalid borrower type."))
		query = query.where(loan.borrower_type == filters.borrower_type)
	if filters.borrower:
		if not isinstance(filters.borrower, str):
			frappe.throw(_("Invalid borrower."))
		query = query.where(loan.borrower == filters.borrower)
	rows = query.orderby(loan.due_on).run(as_dict=True)
	rate = frappe.db.get_single_value("Library Settings", "fine_per_day")
	for row in rows:
		end = row.returned_on or as_of
		row.overdue_days = max(0, date_diff(end, row.due_on))
		row.estimated_fine = (
			calculate_fine(row.due_on, as_of, rate) if row.status == "Issued" else row.fine_amount
		)
	columns = [
		{
			"fieldname": "name",
			"label": _("Circulation"),
			"fieldtype": "Link",
			"options": "Library Circulation",
			"width": 190,
		},
		{
			"fieldname": "copy",
			"label": _("Copy"),
			"fieldtype": "Link",
			"options": "Library Copy",
			"width": 140,
		},
		{"fieldname": "barcode", "label": _("Barcode"), "fieldtype": "Data", "width": 120},
		{
			"fieldname": "article",
			"label": _("Article"),
			"fieldtype": "Link",
			"options": "Article",
			"width": 180,
		},
		{"fieldname": "borrower_type", "label": _("Borrower Type"), "fieldtype": "Data", "width": 110},
		{
			"fieldname": "borrower",
			"label": _("Borrower"),
			"fieldtype": "Dynamic Link",
			"options": "borrower_type",
			"width": 160,
		},
		{"fieldname": "due_on", "label": _("Due On"), "fieldtype": "Date", "width": 110},
		{"fieldname": "returned_on", "label": _("Returned On"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "overdue_days", "label": _("Overdue Days"), "fieldtype": "Int", "width": 110},
		{
			"fieldname": "estimated_fine",
			"label": _("Estimated / Recorded Fine"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 190,
		},
		{"fieldname": "fine_status", "label": _("Fine Status"), "fieldtype": "Data", "width": 110},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 90,
		},
	]
	return (
		columns,
		rows,
		_(
			"Unreturned fines are estimates at the current daily rate. Return the copy to record the fine. Employee fines are never invoiced."
		),
	)
