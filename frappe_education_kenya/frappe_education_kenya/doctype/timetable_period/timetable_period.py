from frappe.model.document import Document

from frappe_education_kenya.timetable import validate_period


class TimetablePeriod(Document):
	def validate(self):
		validate_period(self)
