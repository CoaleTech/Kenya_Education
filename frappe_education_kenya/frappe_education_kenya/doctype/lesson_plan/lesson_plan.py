import frappe
from frappe import _
from frappe.model.document import Document

from frappe_education_kenya.teaching import prevent_preparation_delete, validate_preparation


class LessonPlan(Document):
	def validate(self):
		validate_preparation(self)
		scheme = frappe.get_doc("Scheme of Work", self.scheme_of_work)
		frappe.has_permission("Scheme of Work", "read", doc=scheme, throw=True)
		if scheme.workflow_state != "Approved" or (scheme.instructor, scheme.course) != (
			self.instructor,
			self.course,
		):
			frappe.throw(_("Select an approved scheme for the same Instructor and Course."))
		if self.scheme_week not in {row.name for row in scheme.weeks}:
			frappe.throw(_("Select a week belonging to the approved Scheme of Work."))

	def on_trash(self):
		prevent_preparation_delete(self)
