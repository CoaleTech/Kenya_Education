"""Loan policy configuration."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from frappe_education_kenya.library import calculate_fine


class LibrarySettings(Document):
	def validate(self):
		for field in ("loan_days", "max_loans_student", "max_loans_staff"):
			if cint(self.get(field)) <= 0:
				frappe.throw(_("{0} must be a positive whole number.").format(_(self.meta.get_label(field))))
		calculate_fine("2026-01-01", "2026-01-02", self.fine_per_day)
		if self.fine_item:
			item = frappe.get_doc("Item", self.fine_item)
			if item.disabled or not item.is_sales_item or item.is_stock_item or item.is_fixed_asset:
				frappe.throw(_("The Fine Item must be an enabled, non-stock sales item."))
