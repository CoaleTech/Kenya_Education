"""Append-only circulation history with service-only transitions."""

import frappe
from frappe import _
from frappe.model.document import Document

from frappe_education_kenya.library import require_operation


class LibraryCirculation(Document):
	def validate(self):
		action = require_operation(self, {"issue", "return", "waive", "invoice"})
		# Frappe resets permlevel-1 input before validate for Librarians. Set the derived
		# status here, after that reset, without granting them a fine-status write permission.
		if action == "issue":
			self.fine_status = "None"
		elif action == "return":
			self.fine_status = "Pending" if self.fine_amount else "None"

	def on_trash(self):
		frappe.throw(_("Circulation history cannot be deleted."), frappe.PermissionError)

	def before_rename(self, old, new, merge=False):
		frappe.throw(_("Circulation history cannot be renamed or merged."), frappe.PermissionError)
