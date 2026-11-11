"""Controller for Transport Route."""

from frappe.model.document import Document

from frappe_education_kenya.transport import validate_fares


class TransportRoute(Document):
	def validate(self):
		validate_fares(self.fares)
