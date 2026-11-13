"""Day Scholar / Boarder billing guards.

Education bills through Fee Structure -> Fee Schedule -> Sales Invoice, and
Fee Schedule only separates students by `Program Enrollment.student_category`.
These hooks keep that category filled in and stop a schedule from being built
against the wrong (or no) category.
"""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate


def set_enrollment_category(doc, method=None):
	"""Program Enrollment.validate: default the category from the student's boarder status."""
	if not (doc.student and doc.academic_year):
		return  # mandatory-field validation reports these
	if not doc.student_category:
		# Kenya Student Category names equal the `kenya_boarder_status` options.
		doc.student_category = frappe.db.get_value("Student", doc.student, "kenya_boarder_status")
	if doc.student_category:
		return
	# Past years may stay blank (history); current and future years bill from this field.
	if getdate(frappe.db.get_value("Academic Year", doc.academic_year, "year_end_date")) >= getdate(
		nowdate()
	):
		frappe.throw(
			_(
				"Set the Student Category (or the Boarder Status on student {0}) before enrolling "
				"them in {1}. Fee Schedules bill Day Scholars and Boarders by this category."
			).format(doc.student, doc.academic_year)
		)


def validate_schedule_category(doc, method=None):
	"""Fee Schedule.validate: a schedule bills exactly one category, the one its structure was priced for."""
	if not doc.student_category:
		frappe.throw(
			_("Student Category is required: a Fee Schedule without one bills every enrolled student.")
		)
	structure_category = frappe.db.get_value("Fee Structure", doc.fee_structure, "student_category")
	if doc.student_category != structure_category:
		frappe.throw(
			_(
				"Fee Schedule category {0} does not match Fee Structure {1}, which is for category {2}."
			).format(doc.student_category, doc.fee_structure, structure_category or _("(none)"))
		)


def validate_kenya_fee_structure(doc, method=None):
	"""Fee Structure.validate: a structure names its Student Category; Kenya fee conventions are warned on.

	A Fee Schedule bills the students of one category from the structure of that category.
	Nothing adds Transport or Meals components automatically; add them as Fee Components.
	"""
	if not doc.get("student_category"):
		frappe.throw(
			_(
				"Student Category is required on a Fee Structure so Day Scholars and Boarders are billed "
				"from separate structures."
			)
		)

	if doc.get("kenya_is_government_regulated") and not doc.get("kenya_cbc_level"):
		frappe.msgprint(
			_("Government-regulated fee structures should specify a CBC Level for MoE reporting."),
			indicator="orange",
			alert=True,
		)
