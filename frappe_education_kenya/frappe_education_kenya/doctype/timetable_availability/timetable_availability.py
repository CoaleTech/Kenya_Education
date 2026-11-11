from frappe.model.document import Document

from frappe_education_kenya.timetable import validate_availability


class TimetableAvailability(Document):
	def validate(self):
		validate_availability(self)
