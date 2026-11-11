import frappe
from frappe import _


def execute(filters=None):
	frappe.only_for(["Bursar", "Head Teacher"])
	frappe.has_permission("Fee Pledge", "report", throw=True)
	filters = frappe._dict(filters or {})
	query_filters = {}
	if filters.get("student"):
		if not isinstance(filters.student, str):
			frappe.throw(_("Invalid student filter"))
		query_filters["student"] = filters.student

	columns = [
		{"label": "Name", "fieldname": "name", "fieldtype": "Link", "width": 160, "options": "Fee Pledge"},
		{"label": "Student", "fieldname": "student", "fieldtype": "Link", "width": 160, "options": "Student"},
		{
			"label": "Guardian",
			"fieldname": "guardian",
			"fieldtype": "Link",
			"width": 160,
			"options": "Guardian",
		},
		{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 160},
		{"label": "Met Amount", "fieldname": "met_amount", "fieldtype": "Currency", "width": 160},
		{"label": "Due Date", "fieldname": "due_date", "fieldtype": "Date", "width": 160},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 160},
	]
	for column in columns:
		column["label"] = _(column["label"])
	return columns, frappe.get_list(
		"Fee Pledge",
		filters=query_filters,
		fields=["name", "student", "guardian", "amount", "met_amount", "due_date", "status"],
		limit_page_length=0,
		order_by="creation desc",
	)
