"""Controller for Transport Subscription."""

from frappe.model.document import Document

from frappe_education_kenya.transport import validate_subscription


class TransportSubscription(Document):
	def validate(self):
		validate_subscription(self)
