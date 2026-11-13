"""CBC Student Settings is now the Students tab of Education Kenya Settings: move its values over.

Runs before the doctype sync, which then deletes the orphaned CBC Student Settings and CBC Fee
Settings pages (the fee page had no fields left).
"""

import frappe
from frappe.model import no_value_fields, table_fields

OLD = "CBC Student Settings"
NEW = "Education Kenya Settings"


def execute():
	if not frappe.db.exists("DocType", OLD):
		return

	fields = frappe.get_meta(OLD).fields  # read from the DB: the doctype's files are already gone
	scalars = [f.fieldname for f in fields if f.fieldtype not in no_value_fields]
	singles = frappe.qb.DocType("Singles")
	rows = (
		frappe.qb.from_(singles)
		.select(singles.field, singles.value)
		.where(singles.doctype == OLD)
		.where(singles.field.isin(scalars))
		.run()
	)
	for field, value in rows:
		frappe.db.set_single_value(NEW, field, value, update_modified=False)

	# Child rows (program level mapping, special needs categories, boarding types) follow their parent.
	for field in (f for f in fields if f.fieldtype in table_fields):
		frappe.db.set_value(
			field.options,
			{"parent": OLD, "parenttype": OLD, "parentfield": field.fieldname},
			{"parent": NEW, "parenttype": NEW},
			update_modified=False,
		)
