import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate, nowdate

from frappe_education_kenya.bursary import money, pledge_total


class FeePledge(Document):
	def validate(self):
		money(self.amount)
		if getdate(self.due_date) < getdate(self.pledge_date):
			frappe.throw(_("Due date cannot precede pledge date"))
		if self.reminder_days_before is None:
			self.reminder_days_before = (
				frappe.db.get_single_value("Education Settings", "kenya_pledge_reminder_days") or 3
			)
		if cint(self.reminder_days_before) < 0:
			frappe.throw(_("Reminder days cannot be negative"))
		student = frappe.get_doc("Student", self.student)
		if self.guardian not in [row.guardian for row in student.guardians]:
			frappe.throw(_("Guardian is not linked to this student"))
		if self.fees and frappe.db.get_value("Fees", self.fees, "student") != self.student:
			frappe.throw(_("Fees belongs to another student"))
		old = self.get_doc_before_save()
		if old and any(
			self.get(f) != old.get(f) for f in ("student", "guardian", "fees", "amount", "pledge_date")
		):
			frappe.throw(_("Create a new pledge to change its parties or amount"))
		if not self.flags.finance_action:
			keys = ("sent_on", "channel", "result")
			previous = [tuple(r.get(f) for f in keys) for r in old.reminders] if old else []
			if [tuple(r.get(f) for f in keys) for r in self.reminders] != previous:
				frappe.throw(_("Reminder logs are maintained by the scheduler"))
		if self.status == "Cancelled" and (not old or old.status != "Cancelled"):
			frappe.only_for(["Bursar"])
		self.met_amount = float(pledge_total(self.name)) if not self.is_new() else 0
		if old and old.status == "Cancelled":
			self.status = "Cancelled"
		elif self.status != "Cancelled":
			self.status = (
				"Met"
				if self.met_amount >= self.amount
				else "Broken"
				if getdate(self.due_date) < getdate(nowdate())
				else "Partly Met"
				if self.met_amount
				else "Open"
			)

	def on_trash(self):
		if self.met_amount or self.reminders:
			frappe.throw(_("Pledges with payments or reminder logs cannot be deleted"))
