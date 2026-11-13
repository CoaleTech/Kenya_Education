"""Tests for the Kenya Student field validation and NEMIS sync hooks driven by Education Kenya Settings."""

import frappe
from frappe.tests.utils import FrappeTestCase

from frappe_education_kenya.frappe_education_kenya.doctype.education_kenya_settings.education_kenya_settings import (
	sync_student_to_nemis_fields,
	validate_nemis_data_completeness,
	validate_student_kenya_fields,
)
from frappe_education_kenya.patches.v1_0_0.move_communications_settings_to_education_settings import execute

TEST_EMAIL = "kenya.student.settings.test@example.com"


class TestEducationKenyaSettingsHooks(FrappeTestCase):
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


class TestKenyaTableMultiSelect(FrappeTestCase):
	def test_every_table_multiselect_child_has_a_link_field(self):
		# Desk throws on render, leaving a blank form, when the child table has no Link field.
		bad = []
		for name in frappe.get_all("DocType", filters={"module": "Frappe Education Kenya"}, pluck="name"):
			for df in frappe.get_meta(name).get("fields", {"fieldtype": "Table MultiSelect"}):
				if not any(f.fieldtype == "Link" for f in frappe.get_meta(df.options).fields):
					bad.append(f"{name}.{df.fieldname} -> {df.options}")
		self.assertEqual(bad, [])


class TestMoveCommunicationsSettings(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def stored(self, doctype):
		return dict(frappe.db.sql("select field, value from tabSingles where doctype = %s", doctype))

	def test_values_move_to_education_settings_and_are_deleted(self):
		frappe.db.set_single_value("Education Kenya Settings", "enable_scheduled_messages", "1")
		frappe.db.set_single_value("Education Kenya Settings", "pledge_reminder_days", "5")
		execute()
		new = self.stored("Education Settings")
		self.assertEqual(
			(new["kenya_enable_scheduled_messages"], new["kenya_pledge_reminder_days"]), ("1", "5")
		)
		old = self.stored("Education Kenya Settings")
		self.assertFalse({"enable_scheduled_messages", "pledge_reminder_days"} & set(old))
		execute()  # second run is a no-op
		self.assertEqual(self.stored("Education Settings")["kenya_pledge_reminder_days"], "5")
