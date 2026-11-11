"""Catalogue copies; circulation owns the Issued state and protects history."""

import frappe
from frappe import _
from frappe.model.document import Document

from frappe_education_kenya.library import _OPERATION, _active_loans, _lock


class LibraryCopy(Document):
	def before_insert(self):
		# Naming uses the barcode before validate runs.
		self._clean_barcode()

	def _clean_barcode(self):
		if not isinstance(self.barcode, str) or not self.barcode.strip():
			frappe.throw(_("A barcode is required."))
		self.barcode = self.barcode.strip()

	def validate(self):
		self._clean_barcode()
		internal = _OPERATION.get() == ("copy", self.name)
		if self.is_new():
			if self.status == "Issued":
				frappe.throw(_("Use Issue Copy to issue a library copy."), frappe.PermissionError)
			return
		_lock("Library Copy", self.name)
		old = frappe.db.get_value("Library Copy", self.name, ["article", "barcode", "status"], as_dict=True)
		if frappe.db.exists("Library Circulation", {"copy": self.name}):
			if self.article != old.article or self.barcode != old.barcode:
				frappe.throw(_("A copy with circulation history cannot change its article or barcode."))
		if not internal:
			if self.status == "Issued" or old.status == "Issued" or _active_loans(copy=self.name):
				if self.status != old.status:
					frappe.throw(
						_("Use the library Issue or Return action to change circulation status."),
						frappe.PermissionError,
					)
				if self.status == "Issued" and old.status != "Issued":
					frappe.throw(_("Use Issue Copy to issue a library copy."), frappe.PermissionError)

	def on_trash(self):
		_lock("Library Copy", self.name)
		if frappe.db.exists("Library Circulation", {"copy": self.name}):
			frappe.throw(_("A copy with circulation history cannot be deleted; mark it Withdrawn instead."))
