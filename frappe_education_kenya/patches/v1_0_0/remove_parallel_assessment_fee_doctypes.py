"""Drop the parallel CBC assessment/fee DocTypes.

These duplicated base Education functionality and have been collapsed into
extensions of the base DocTypes:

  * CBC Assessment / CBC Assessment Result / CBC Assessment Learning Outcome
    -> base Assessment Plan / Assessment Result + a "CBC Performance Levels"
       Grading Scale + custom fields.
  * CBC Fee Component -> base Fee Component / Fee Category on Fee Structure.

Removing the DocType JSON from the app does not drop the DB tables, so this
patch deletes the DocType records (which drops their tables). All were empty.
"""

import frappe

REMOVED_DOCTYPES = [
	"CBC Assessment Result",
	"CBC Assessment Learning Outcome",
	"CBC Assessment",
	"CBC Fee Component",
]


def execute():
	for doctype in REMOVED_DOCTYPES:
		if frappe.db.exists("DocType", doctype):
			# Guard: only drop if empty; a non-empty table means unexpected data.
			if frappe.db.count(doctype):
				frappe.log_error(
					title="Skipped dropping non-empty DocType",
					message=f"{doctype} still has rows; leaving it in place.",
				)
				continue
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)

		# delete_doc does not always drop the backing table on this version;
		# drop it explicitly so no orphan `tab<DocType>` table is left behind.
		frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{doctype}`")
