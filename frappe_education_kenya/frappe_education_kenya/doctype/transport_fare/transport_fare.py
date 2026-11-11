from frappe.model.document import Document


class TransportFare(Document):
	"""Owned by Transport Route; dates and amounts validate with the full fare schedule."""
