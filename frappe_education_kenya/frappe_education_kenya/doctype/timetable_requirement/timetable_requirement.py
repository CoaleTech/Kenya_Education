from frappe.model.document import Document

from frappe_education_kenya.timetable import validate_requirement


class TimetableRequirement(Document):
	def validate(self):
		validate_requirement(self)
