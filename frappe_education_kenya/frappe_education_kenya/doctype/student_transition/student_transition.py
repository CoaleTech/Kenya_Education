"""Student Transition: an approved movement of a student between CBC levels or out of the school.

Submitting a transition is the approval. It keeps the Student register in step:
a level change sets `kenya_cbc_level`; an exit (transfer out, dropout, graduation)
disables the student and records the leaving date and reason. Cancelling reverses it.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

EXITS = ("Transfer Out", "Dropout", "Graduation")
LEVEL_CHANGES = ("Automatic Progression", "Exam-Based Promotion")


class StudentTransition(Document):
	def validate(self):
		student = frappe.db.get_value("Student", self.student, ["student_name", "joining_date"], as_dict=True)
		self.student_name = student.student_name

		if self.transition_type in EXITS:
			if student.joining_date and getdate(self.transition_date) < getdate(student.joining_date):
				frappe.throw(_("A student cannot leave before joining on {0}.").format(student.joining_date))
		elif not self.to_level:
			frappe.throw(_("To CBC Level is required for {0}.").format(_(self.transition_type)))

		if self.transition_type in LEVEL_CHANGES and not self.from_level:
			frappe.throw(_("From CBC Level is required for {0}.").format(_(self.transition_type)))

	def before_submit(self):
		self.approved_by = frappe.session.user
		self.approval_date = today()

	def on_submit(self):
		sync_student(self.student)

	def on_cancel(self):
		sync_student(self.student, undone=self)


def sync_student(student, undone=None):
	"""Make the Student register match the student's approved transitions.

	The state is derived, not accumulated: the latest approved transition decides whether the
	student has left, and the latest approved level change decides the level. That is what lets a
	cancelled or back-dated transition reverse cleanly. `undone` is the transition being cancelled.
	A later non-exit transition re-admits a student only if the register holds a leaving date, so a
	student disabled for another reason stays disabled.
	"""
	rows = frappe.get_all(
		"Student Transition",
		filters={"student": student, "docstatus": 1},
		fields=["transition_type", "transition_date", "to_level", "to_school"],
		order_by="transition_date desc, creation desc",
	)
	latest = rows[0] if rows else None
	levelled = next((r for r in rows if r.transition_type not in EXITS), None)

	values = {}
	if levelled:
		values["kenya_cbc_level"] = levelled.to_level
	elif undone and undone.transition_type not in EXITS:
		values["kenya_cbc_level"] = undone.from_level

	if latest and latest.transition_type in EXITS:
		reason = latest.transition_type
		if latest.to_school:
			reason += f" - {latest.to_school}"
		values.update(enabled=0, date_of_leaving=latest.transition_date, reason_for_leaving=reason)
	elif frappe.db.get_value("Student", student, "date_of_leaving"):
		values.update(enabled=1, date_of_leaving=None, reason_for_leaving=None)

	if values:
		frappe.db.set_value("Student", student, values)


def after_program_enrollment(doc, method=None):
	"""On-submit hook for Program Enrollment: records and approves the matching transition.

	Resolves the enrolled Program's CBC Level (via the `cbc_level_mapping`
	custom field added during install) and logs the progression so MoE
	transition reporting has a complete audit trail. Enrollment is the approval.
	"""
	if not doc.get("student") or not doc.get("program"):
		return

	to_level = frappe.db.get_value("Program", doc.program, "cbc_level_mapping")
	if not to_level:
		# Program has no CBC level mapping configured; nothing to record.
		return

	if frappe.db.exists("Student Transition", {"program_enrollment": doc.name, "docstatus": 1}):
		return

	from_program = from_level = None
	previous_enrollment = frappe.get_all(
		"Program Enrollment",
		filters={"student": doc.student, "name": ["!=", doc.name], "docstatus": 1},
		fields=["program"],
		order_by="enrollment_date desc",
		limit_page_length=1,
	)
	if previous_enrollment:
		from_program = previous_enrollment[0].program
		from_level = frappe.db.get_value("Program", from_program, "cbc_level_mapping")

	transition = frappe.new_doc("Student Transition")
	transition.student = doc.student
	transition.transition_type = "Automatic Progression" if from_level else "Transfer In"
	transition.transition_date = doc.get("enrollment_date") or today()
	transition.from_level = from_level
	transition.from_program = from_program
	transition.to_level = to_level
	transition.to_program = doc.program
	transition.program_enrollment = doc.name
	transition.flags.ignore_permissions = True
	transition.insert()
	transition.submit()


def after_program_enrollment_cancel(doc, method=None):
	"""On-cancel hook for Program Enrollment: cancels the transition it created."""
	for name in frappe.get_all(
		"Student Transition", filters={"program_enrollment": doc.name, "docstatus": 1}, pluck="name"
	):
		transition = frappe.get_doc("Student Transition", name)
		transition.flags.ignore_permissions = True
		transition.cancel()
