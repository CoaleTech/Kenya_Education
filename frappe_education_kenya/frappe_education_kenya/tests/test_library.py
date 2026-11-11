"""Library circulation regressions. Every DB test runs as Administrator and rolls back."""

import unittest
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime, today

from frappe_education_kenya import library

GUARDIAN = "guardian@example.invalid"


class TestLibraryPure(unittest.TestCase):
	"""No site or database needed."""

	def test_fine_counts_whole_overdue_days_and_rounds_half_up(self):
		self.assertEqual(library.calculate_fine("2026-01-10", "2026-01-13 09:00:00", "0.335"), 1.01)
		self.assertEqual(library.calculate_fine("2026-01-10", "2026-01-09", 50), 0)

	def test_operation_capability_is_scoped(self):
		doc = frappe._dict(name="X")
		with library._operation("return", "X"):
			self.assertEqual(library.require_operation(doc, {"return"}), "return")
		self.assertIsNone(library._OPERATION.get())

	def test_guardian_hooks_are_read_only_and_row_scoped(self):
		doc = frappe._dict(borrower_type="Student", borrower="S1", name="C1")
		with (
			patch.object(library, "_staff", return_value=False),
			patch.object(library, "linked_students", return_value=["S1"]),
		):
			self.assertTrue(library.circulation_has_permission(doc, "read", GUARDIAN))
			self.assertFalse(library.circulation_has_permission(doc, "write", GUARDIAN))
			other = frappe._dict(doc, borrower="S2")
			self.assertFalse(library.circulation_has_permission(other, "read", GUARDIAN))
			self.assertFalse(library.copy_has_permission(doc, "delete", GUARDIAN))
		with (
			patch.object(library, "_staff", return_value=False),
			patch.object(library, "linked_students", return_value=[]),
		):
			self.assertEqual(library.circulation_query_conditions(GUARDIAN), "1=0")
			self.assertEqual(library.copy_query_conditions(GUARDIAN), "1=0")


class TestLibraryCirculation(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.savepoint("library_test")
		settings = frappe.get_single("Library Settings")
		settings.update({"loan_days": 7, "max_loans_student": 1, "max_loans_staff": 2, "fine_per_day": 10})
		settings.save()
		if not frappe.db.get_single_value("Education Kenya Settings", "default_currency"):
			frappe.db.set_single_value("Education Kenya Settings", "default_currency", "KES")
		title = f"EDK Library {frappe.generate_hash(length=8)}"
		self.article = frappe.get_doc({"doctype": "Article", "title": title}).insert()
		customer_name = f"EDK Library {frappe.generate_hash(length=8)}"
		self.customer = frappe.get_doc(
			{"doctype": "Customer", "name": customer_name, "customer_name": customer_name}
		)
		self.customer.db_insert()
		# db_insert avoids Student user creation and welcome email side effects.
		self.student = frappe.get_doc(
			{
				"doctype": "Student",
				"name": f"EDK-LIB-{frappe.generate_hash(length=8)}",
				"first_name": "Library",
				"student_email_id": f"{frappe.generate_hash(length=8)}@example.invalid",
				"enabled": 1,
				"customer": self.customer.name,
			}
		)
		self.student.db_insert()

	def tearDown(self):
		frappe.db.rollback(save_point="library_test")
		frappe.set_user("Administrator")

	def copy(self):
		barcode = f" EDK-{frappe.generate_hash(length=8)} "
		return frappe.get_doc(
			{"doctype": "Library Copy", "article": self.article.name, "barcode": barcode}
		).insert()

	def issue(self, copy, days_overdue=0):
		name = library.issue_copy(copy.barcode, "Student", self.student.name)["name"]
		if days_overdue:
			frappe.db.set_value("Library Circulation", name, "due_on", add_days(today(), -days_overdue))
		return name

	def test_issue_return_limit_and_fine(self):
		copy, second = self.copy(), self.copy()
		self.assertEqual(copy.name, copy.barcode)
		name = self.issue(copy, days_overdue=3)
		self.assertEqual(frappe.db.get_value("Library Copy", copy.name, "status"), "Issued")
		with self.assertRaises(frappe.ValidationError):
			library.issue_copy(copy.barcode, "Student", self.student.name)
		with self.assertRaises(frappe.ValidationError):
			library.issue_copy(second.barcode, "Student", self.student.name)
		library.return_copy(copy.barcode)
		loan = frappe.get_doc("Library Circulation", name)
		self.assertEqual((loan.status, loan.fine_amount, loan.fine_status), ("Returned", 30, "Pending"))
		self.assertEqual(frappe.db.get_value("Library Copy", copy.name, "status"), "Available")

	def test_inactive_borrower_is_rejected(self):
		frappe.db.set_value("Student", self.student.name, "enabled", 0)
		with self.assertRaises(frappe.ValidationError):
			self.issue(self.copy())

	def test_direct_crud_bypass_is_rejected(self):
		copy = self.copy()
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "Library Circulation",
					"copy": copy.name,
					"borrower_type": "Student",
					"borrower": self.student.name,
					"issued_on": now_datetime(),
					"due_on": today(),
					"currency": "KES",
				}
			).insert()
		copy.status = "Issued"
		with self.assertRaises(frappe.PermissionError):
			copy.save()
		loan = frappe.get_doc("Library Circulation", self.issue(copy.reload()))
		loan.fine_status = "Waived"
		with self.assertRaises(frappe.PermissionError):
			loan.save()
		with self.assertRaises(frappe.PermissionError):
			loan.delete()
		with self.assertRaises(frappe.ValidationError):
			copy.reload().delete()

	def test_waiver_records_reason_and_blocks_invoice(self):
		copy = self.copy()
		name = self.issue(copy, days_overdue=1)
		library.return_copy(copy.barcode)
		with self.assertRaises(frappe.ValidationError):
			library.waive_fine(name, " ")
		library.waive_fine(name, "Hardship approved")
		loan = frappe.get_doc("Library Circulation", name)
		self.assertEqual(
			(loan.fine_status, loan.waiver_reason, loan.waived_by),
			("Waived", "Hardship approved", "Administrator"),
		)
		with self.assertRaises(frappe.ValidationError):
			library.invoice_fine(name)

	def test_employee_fines_are_record_only(self):
		loan = frappe.get_doc(
			{
				"doctype": "Library Circulation",
				"name": f"EDK-LIB-EMP-{frappe.generate_hash(length=6)}",
				"copy": self.copy().name,
				"borrower_type": "Employee",
				"borrower": "HR-EMP-TEST",
				"issued_on": now_datetime(),
				"due_on": today(),
				"returned_on": now_datetime(),
				"status": "Returned",
				"fine_amount": 20,
				"fine_status": "Pending",
				"currency": "KES",
			}
		)
		loan.db_insert()
		with self.assertRaisesRegex(frappe.ValidationError, "record-only"):
			library.invoice_fine(loan.name)

	def test_student_fine_invoice_is_idempotent_draft(self):
		company = frappe.get_all("Company", pluck="name", limit=1)
		self.assertTrue(company, "Fine invoice test needs a Company")
		company = company[0]
		account = frappe.get_all(
			"Account",
			filters={"company": company, "root_type": "Income", "is_group": 0, "disabled": 0},
			pluck="name",
			limit=1,
		)
		center = frappe.get_all(
			"Cost Center", filters={"company": company, "is_group": 0}, pluck="name", limit=1
		)
		item_group = frappe.get_all("Item Group", filters={"is_group": 0}, pluck="name", limit=1)
		self.assertTrue(account and center and item_group, "Fine invoice test needs master data")
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": f"EDK-LIB-FINE-{frappe.generate_hash(length=6)}",
				"item_group": item_group[0],
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"is_sales_item": 1,
			}
		).insert()
		for field, value in {
			"company": company,
			"default_fee_account": account[0],
			"cost_center": center[0],
			"default_currency": frappe.db.get_value("Company", company, "default_currency"),
		}.items():
			frappe.db.set_single_value("Education Kenya Settings", field, value)
		frappe.db.set_single_value("Library Settings", "fine_item", item.name)
		price_list = frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": f"EDK Fines {frappe.generate_hash(length=6)}",
				"currency": frappe.db.get_value("Company", company, "default_currency"),
				"selling": 1,
			}
		).insert()
		frappe.db.set_single_value("Selling Settings", "selling_price_list", price_list.name)
		copy = self.copy()
		name = self.issue(copy, days_overdue=2)
		library.return_copy(copy.barcode)
		first = library.invoice_fine(name)["invoice"]
		self.assertEqual(library.invoice_fine(name)["invoice"], first)
		invoice = frappe.get_doc("Sales Invoice", first)
		self.assertEqual(
			(invoice.docstatus, invoice.customer, invoice.grand_total), (0, self.customer.name, 20)
		)
		self.assertEqual(frappe.db.get_value("Library Circulation", name, "fine_status"), "Invoiced")
