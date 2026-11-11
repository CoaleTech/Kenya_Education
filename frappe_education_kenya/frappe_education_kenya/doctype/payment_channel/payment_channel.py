import frappe
from frappe import _
from frappe.model.document import Document


class PaymentChannel(Document):
	def validate(self):
		frappe.only_for(["System Manager"])
		account = frappe.get_doc("Account", self.bank_account)
		company = frappe.db.get_single_value("Education Kenya Settings", "company")
		if (
			account.company != company
			or account.is_group
			or account.disabled
			or account.account_type not in ("Bank", "Cash")
		):
			frappe.throw(_("Channel account must be an enabled school bank/cash account"))
		# ERPNext ties a Mode of Payment to a ledger account per company; receipts must follow that link.
		mode_account = frappe.db.get_value(
			"Mode of Payment Account", {"parent": self.mode_of_payment, "company": company}, "default_account"
		)
		if not frappe.db.get_value("Mode of Payment", self.mode_of_payment, "enabled") or (
			mode_account != self.bank_account
		):
			frappe.throw(
				_(
					"Mode of Payment must be enabled with the channel account as its account for the school company"
				)
			)
		# The ingress endpoint finds its channel by provider and shortcode.
		if self.enabled and frappe.db.exists(
			"Payment Channel",
			{"provider": self.provider, "shortcode": self.shortcode, "enabled": 1, "name": ["!=", self.name]},
		):
			frappe.throw(_("Another enabled channel already uses this provider and shortcode"))
