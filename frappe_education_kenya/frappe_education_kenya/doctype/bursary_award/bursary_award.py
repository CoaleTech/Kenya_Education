import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from frappe_education_kenya.bursary import allocation_total, money


class BursaryAward(Document):
	def validate(self):
		money(self.amount)
		if getdate(self.valid_to) < getdate(self.valid_from):
			frappe.throw(_("Validity end cannot precede start"))
		if self.pledge and frappe.db.get_value("Fee Pledge", self.pledge, "student") != self.student:
			frappe.throw(_("Pledge belongs to another student"))
		old = self.get_doc_before_save()
		if self.is_new() and (self.allocations or self.workflow_state not in (None, "Draft")):
			frappe.throw(_("Awards must start in Draft without allocations"))
		if old and old.workflow_state != "Draft":
			if any(
				self.get(f) != old.get(f)
				for f in ("sponsor", "student", "amount", "basis", "valid_from", "valid_to", "pledge")
			):
				frappe.throw(_("Submitted award details are protected"))
		keys = ("reference_doctype", "reference_name", "amount", "payment_entry", "allocated_on")
		if (
			old
			and not self.flags.finance_action
			and [tuple(r.get(f) for f in keys) for r in self.allocations]
			!= [tuple(r.get(f) for f in keys) for r in old.allocations]
		):
			frappe.throw(_("Use Allocate to change award allocations"))
		if (
			old
			and self.workflow_state == "Allocated"
			and old.workflow_state != "Allocated"
			and not self.flags.finance_action
		):
			frappe.throw(
				_("Use the Allocate Bursary button to choose a target and create a draft Payment Entry")
			)
		if (
			old
			and self.workflow_state in ("Approved", "Rejected")
			and old.workflow_state != self.workflow_state
		):
			frappe.only_for(["Head Teacher"])
		self.allocated_amount = float(allocation_total(self.allocations))
		if self.allocated_amount > self.amount:
			frappe.throw(_("Allocation exceeds the award amount"))

	def on_trash(self):
		if self.workflow_state != "Draft" or self.allocations:
			frappe.throw(_("Only unallocated Draft awards can be deleted"))
