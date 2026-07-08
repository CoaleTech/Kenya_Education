"""Tests for CBC Student Settings Kenya field validation and NEMIS sync hooks."""

import frappe
from frappe.tests.utils import FrappeTestCase

from frappe_education_kenya.frappe_education_kenya.doctype.cbc_student_settings.cbc_student_settings import (
	sync_student_to_nemis_fields,
	validate_nemis_data_completeness,
	validate_student_kenya_fields,
)

TEST_EMAIL = "kenya.student.settings.test@example.com"


class TestCBCStudentSettingsHooks(FrappeTestCase):
	def setUp(self):
		if frappe.db.exists("Student", {"student_email_id": TEST_EMAIL}):
			frappe.delete_doc(
				"Student",
				frappe.db.get_value("Student", {"student_email_id": TEST_EMAIL}),
				force=True,
				ignore_permissions=True,
			)

	def test_validate_does_not_raise_without_identifiers(self):
		doc = frappe.new_doc("Student")
		doc.first_name = "Kenya"
		doc.last_name = "Validate"
		doc.student_email_id = TEST_EMAIL
		# validate_student_kenya_fields should only msgprint, never block save.
		validate_student_kenya_fields(doc)
		doc.insert(ignore_permissions=True)

	def test_sync_normalizes_upin_and_nemis_number(self):
		doc = frappe.new_doc("Student")
		doc.first_name = "Kenya"
		doc.last_name = "Sync"
		doc.student_email_id = TEST_EMAIL
		doc.kenya_upin = " upin123 "
		doc.kenya_nemis_number = " nemis456 "
		doc.insert(ignore_permissions=True)

		sync_student_to_nemis_fields(doc)

		refreshed = frappe.db.get_value(
			"Student", doc.name, ["kenya_upin", "kenya_nemis_number"], as_dict=True
		)
		self.assertEqual(refreshed.kenya_upin, "UPIN123")
		self.assertEqual(refreshed.kenya_nemis_number, "nemis456")

	def test_sync_is_noop_when_already_normalized(self):
		doc = frappe.new_doc("Student")
		doc.first_name = "Kenya"
		doc.last_name = "AlreadyClean"
		doc.student_email_id = TEST_EMAIL
		doc.kenya_upin = "CLEAN123"
		doc.insert(ignore_permissions=True)

		modified_before = frappe.db.get_value("Student", doc.name, "modified")
		sync_student_to_nemis_fields(doc)
		modified_after = frappe.db.get_value("Student", doc.name, "modified")
		self.assertEqual(modified_before, modified_after)

	def test_validate_nemis_completeness_does_not_raise(self):
		# Exercises the scheduled task end-to-end; should not raise regardless
		# of whether incomplete records exist.
		validate_nemis_data_completeness()

	def tearDown(self):
		frappe.db.rollback()
