from frappe.model.document import Document

from frappe_education_kenya.pathways import validate_choice


class StudentPathwayChoice(Document):
	def validate(self):
		validate_choice(self)
