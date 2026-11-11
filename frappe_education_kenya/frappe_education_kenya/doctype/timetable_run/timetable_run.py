from frappe.model.document import Document

from frappe_education_kenya.timetable import protect_run_deletion, validate_run


class TimetableRun(Document):
	def validate(self):
		validate_run(self)

	def on_trash(self):
		protect_run_deletion(self)
