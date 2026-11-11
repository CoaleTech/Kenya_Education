import frappe
from frappe import _
from frappe.model.document import Document

from frappe_education_kenya.bursary import invoice_for, money, settings


class ElectronicCollection(Document):
	def validate(self):
		money(self.amount)
		old = self.get_doc_before_save()
		if self.is_new():
			if (
				self.workflow_state not in (None, "New")
				or self.payment_entry
				or self.student
				or self.sales_invoice
				or self.fees
			):
				frappe.throw(_("Collections must enter as unmatched New inbox records"))
			if self.raw_payload:
				frappe.only_for(["System Manager"])
		if old:
			if any(
				self.get(f) != old.get(f)
				for f in (
					"channel",
					"transaction_code",
					"amount",
					"sender",
					"account_reference",
					"received_at",
					"raw_payload",
				)
			):
				frappe.throw(_("Original collection data is immutable"))
			if (
				self.payment_entry != old.payment_entry
				or self.approved_by != old.approved_by
				or self.approved_on != old.approved_on
			):
				frappe.throw(_("Payment linkage and approval audit are maintained by the approval action"))
			if old.status in ("Approved", "Posted", "Rejected"):
				frappe.throw(_("Final collection records are protected"))
		if self.workflow_state == "Posted":
			frappe.throw(_("Posting is only allowed through approval"))
		if self.workflow_state == "Approved":
			frappe.only_for(["Bursar"])
			if not old or old.status != "Matched":
				frappe.throw(_("Only matched collections may be approved"))
		if self.workflow_state in ("Matched", "Approved"):
			if not self.student or self.student != self.account_reference:
				frappe.throw(_("Account reference must exactly match Student ID"))
			if bool(self.fees) == bool(self.sales_invoice):
				frappe.throw(_("Select exactly one Fees or Sales Invoice target"))
			invoice_for(
				self.student,
				self.fees or self.sales_invoice,
				settings(),
				"Fees" if self.fees else "Sales Invoice",
			)
		if self.workflow_state == "Rejected":
			frappe.only_for(["Bursar"])
			if not self.rejection_reason:
				frappe.throw(_("Rejection reason is required"))
		self.status = self.workflow_state or "New"

	def on_update(self):
		if self.status == "Approved":
			from frappe_education_kenya.collections import post_approved

			post_approved(self)

	def on_trash(self):
		frappe.throw(_("Collection inbox audit records cannot be deleted"))
