import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from frappe_education_kenya.teaching import prevent_preparation_delete, validate_preparation


class SchemeofWork(Document):
	def validate(self):
		validate_preparation(self)
		weeks = [cint(row.week_no) for row in self.weeks]
		if not weeks or any(week <= 0 for week in weeks) or len(weeks) != len(set(weeks)):
			frappe.throw(_("Scheme weeks must have distinct positive week numbers."))

	def on_trash(self):
		prevent_preparation_delete(self)
