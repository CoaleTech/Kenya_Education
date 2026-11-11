import frappe
from frappe import _


def execute(filters=None):
	frappe.only_for(["Bursar", "Head Teacher"])
	frappe.has_permission("Bursary Award", "report", throw=True)
	filters = frappe._dict(filters or {})
	query_filters = {}
	if filters.get("student"):
		if not isinstance(filters.student, str):
			frappe.throw(_("Invalid student filter"))
		query_filters["student"] = filters.student

	columns = [
		{"label": "Name", "fieldname": "name", "fieldtype": "Link", "width": 160, "options": "Bursary Award"},
		{"label": "Sponsor", "fieldname": "sponsor", "fieldtype": "Link", "width": 160, "options": "Sponsor"},
		{"label": "Student", "fieldname": "student", "fieldtype": "Link", "width": 160, "options": "Student"},
		{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 160},
		{"label": "Allocated Amount", "fieldname": "allocated_amount", "fieldtype": "Currency", "width": 160},
		{"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Data", "width": 160},
		{"label": "Valid From", "fieldname": "valid_from", "fieldtype": "Date", "width": 160},
		{"label": "Valid To", "fieldname": "valid_to", "fieldtype": "Date", "width": 160},
	]
	for column in columns:
		column["label"] = _(column["label"])
	return columns, frappe.get_list(
		"Bursary Award",
		filters=query_filters,
		fields=[
			"name",
			"sponsor",
			"student",
			"amount",
			"allocated_amount",
			"workflow_state",
			"valid_from",
			"valid_to",
		],
		limit_page_length=0,
		order_by="creation desc",
	)
