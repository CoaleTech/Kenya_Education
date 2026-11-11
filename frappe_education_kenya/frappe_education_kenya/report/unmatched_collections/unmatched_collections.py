import frappe
from frappe import _


def execute(filters=None):
	frappe.only_for(["Bursar", "Head Teacher"])
	frappe.has_permission("Electronic Collection", "report", throw=True)
	filters = frappe._dict(filters or {})
	query_filters = {}
	if filters.get("student"):
		if not isinstance(filters.student, str):
			frappe.throw(_("Invalid student filter"))
		query_filters["student"] = filters.student

	query_filters["status"] = ["in", ["New", "Needs Review", "Matched"]]
	columns = [
		{
			"label": "Name",
			"fieldname": "name",
			"fieldtype": "Link",
			"width": 160,
			"options": "Electronic Collection",
		},
		{
			"label": "Channel",
			"fieldname": "channel",
			"fieldtype": "Link",
			"width": 160,
			"options": "Payment Channel",
		},
		{"label": "Transaction Code", "fieldname": "transaction_code", "fieldtype": "Data", "width": 160},
		{"label": "Account Reference", "fieldname": "account_reference", "fieldtype": "Data", "width": 160},
		{"label": "Student", "fieldname": "student", "fieldtype": "Link", "width": 160, "options": "Student"},
		{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 160},
		{"label": "Received At", "fieldname": "received_at", "fieldtype": "Datetime", "width": 160},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 160},
		{"label": "Rejection Reason", "fieldname": "rejection_reason", "fieldtype": "Data", "width": 160},
	]
	for column in columns:
		column["label"] = _(column["label"])
	return columns, frappe.get_list(
		"Electronic Collection",
		filters=query_filters,
		fields=[
			"name",
			"channel",
			"transaction_code",
			"account_reference",
			"student",
			"amount",
			"received_at",
			"status",
			"rejection_reason",
		],
		limit_page_length=0,
		order_by="creation desc",
	)
