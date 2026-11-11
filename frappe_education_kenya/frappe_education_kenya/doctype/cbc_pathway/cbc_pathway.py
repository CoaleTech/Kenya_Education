from frappe.model.document import Document

from frappe_education_kenya.pathways import validate_pathway


class CBCPathway(Document):
	def validate(self):
		validate_pathway(self)
