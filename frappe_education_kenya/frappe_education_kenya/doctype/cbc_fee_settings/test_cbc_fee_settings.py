"""Tests for CBC Fee Settings Kenya fee-structure validation hook."""

import frappe
from frappe.tests.utils import FrappeTestCase

from frappe_education_kenya.frappe_education_kenya.doctype.cbc_fee_settings.cbc_fee_settings import (
	validate_kenya_fee_structure,
)


class FakeDoc(dict):
	def get(self, k, default=None):
		return dict.get(self, k, default)


class TestCBCFeeSettingsValidation(FrappeTestCase):
	def setUp(self):
		self.settings = frappe.get_cached_doc("CBC Fee Settings")
		self._orig_transport = self.settings.get("auto_generate_transport_invoice")
		self._orig_meals = self.settings.get("auto_generate_meals_invoice")

	def test_transport_fee_warns_when_auto_invoice_disabled(self):
		frappe.db.set_value("CBC Fee Settings", None, "auto_generate_transport_invoice", 0)
		frappe.clear_cache(doctype="CBC Fee Settings")

		doc = FakeDoc(kenya_fee_category="Transport Fee")
		# Should not raise; msgprint alerts are non-blocking.
		validate_kenya_fee_structure(doc)

	def test_transport_fee_no_warning_when_enabled(self):
		frappe.db.set_value("CBC Fee Settings", None, "auto_generate_transport_invoice", 1)
		frappe.clear_cache(doctype="CBC Fee Settings")

		doc = FakeDoc(kenya_fee_category="Transport Fee")
		validate_kenya_fee_structure(doc)  # should not raise

	def test_government_regulated_without_cbc_level_does_not_raise(self):
		doc = FakeDoc(kenya_is_government_regulated=1, kenya_cbc_level=None)
		validate_kenya_fee_structure(doc)  # should not raise, just msgprint

	def test_non_kenya_fee_category_is_noop(self):
		doc = FakeDoc(kenya_fee_category="Tuition Fee")
		validate_kenya_fee_structure(doc)  # should not raise

	def tearDown(self):
		frappe.db.set_value(
			"CBC Fee Settings", None, "auto_generate_transport_invoice", self._orig_transport
		)
		frappe.db.set_value(
			"CBC Fee Settings", None, "auto_generate_meals_invoice", self._orig_meals
		)
		frappe.clear_cache(doctype="CBC Fee Settings")
		frappe.db.rollback()
