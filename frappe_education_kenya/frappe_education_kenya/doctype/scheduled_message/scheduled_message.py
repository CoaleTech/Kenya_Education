import frappe
from frappe import _
from frappe.model.document import Document

from frappe_education_kenya.messaging import validate_message


class ScheduledMessage(Document):
	def validate(self):
		validate_message(self)

	def on_trash(self):
		if self.status != "Draft":
			frappe.throw(_("Scheduled and dispatched messages cannot be deleted."))
