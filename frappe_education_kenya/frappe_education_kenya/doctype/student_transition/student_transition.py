"""Server-side logic for Student Transition: tracks movement between CBC levels."""

import frappe
from frappe.model.document import Document


class StudentTransition(Document):
	def validate(self):
		if self.student and not self.student_name:
			self.student_name = frappe.db.get_value("Student", self.student, "student_name")


def after_program_enrollment(doc, method=None):
	"""On-submit hook for Program Enrollment: auto-creates a Student Transition record.

	Resolves the enrolled Program's CBC Level (via the `cbc_level_mapping`
	custom field added during install) and logs the progression so MoE
	transition reporting has a complete audit trail.
	"""
	if not doc.get("student") or not doc.get("program"):
		return

	to_level = frappe.db.get_value("Program", doc.program, "cbc_level_mapping")
	if not to_level:
		# Program has no CBC level mapping configured; nothing to record.
		return

	# Avoid duplicate transitions for the same enrollment.
	existing = frappe.db.exists(
		"Student Transition",
		{"student": doc.student, "to_level": to_level, "transition_date": doc.get("enrollment_date")},
	)
	if existing:
		return

	from_level = None
	previous_enrollment = frappe.get_all(
		"Program Enrollment",
		filters={"student": doc.student, "name": ["!=", doc.name], "docstatus": 1},
		fields=["program"],
		order_by="enrollment_date desc",
		limit_page_length=1,
	)
	if previous_enrollment:
		from_level = frappe.db.get_value("Program", previous_enrollment[0].program, "cbc_level_mapping")

	transition = frappe.new_doc("Student Transition")
	transition.student = doc.student
	transition.student_name = frappe.db.get_value("Student", doc.student, "student_name")
	transition.transition_type = "Automatic Progression" if from_level else "Transfer In"
	transition.transition_date = doc.get("enrollment_date") or frappe.utils.today()
	transition.from_level = from_level
	transition.to_level = to_level
	transition.insert(ignore_permissions=True)
