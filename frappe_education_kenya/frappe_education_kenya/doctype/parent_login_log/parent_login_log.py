import frappe
from frappe import _
from frappe.model.document import Document


class ParentLoginLog(Document):
	def validate(self):
		if not self.is_new() or not self.flags.from_guardian_login:
			frappe.throw(
				_("Login records are written only by the authenticated session hook."), frappe.PermissionError
			)

	def on_trash(self):
		frappe.throw(_("Login audit records cannot be deleted."), frappe.PermissionError)
