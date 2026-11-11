from frappe.model.document import Document

from frappe_education_kenya.pathways import validate_combination


class CBCSubjectCombination(Document):
	def validate(self):
		validate_combination(self)
