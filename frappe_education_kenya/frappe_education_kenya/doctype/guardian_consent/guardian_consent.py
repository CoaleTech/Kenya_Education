import frappe
from frappe import _
from frappe.model.document import Document

from frappe_education_kenya.parent_ops import validate_consent


class GuardianConsent(Document):
	def validate(self):
		validate_consent(self)

	def on_trash(self):
		frappe.throw(_("Consent history cannot be deleted. Record a revoked decision instead."))
