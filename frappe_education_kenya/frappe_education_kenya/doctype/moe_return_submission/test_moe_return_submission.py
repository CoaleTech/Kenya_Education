"""Tests for MoE Return Submission scheduled tasks."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import formatdate, today

from frappe_education_kenya.frappe_education_kenya.doctype.moe_return_submission.moe_return_submission import (
	auto_generate_monthly_enrolment_return,
	check_upcoming_deadlines,
	generate_daily_attendance_snapshot,
)


class TestMoEReturnSubmission(FrappeTestCase):
	def setUp(self):
		# Clean any pre-existing EMIS-001 submissions for the current period so
		# each test run starts from a known state.
		reporting_period = formatdate(today(), "MMMM yyyy")
		for name in frappe.get_all(
			"MoE Return Submission",
			filters={"template": "EMIS-001", "reporting_period": reporting_period},
			pluck="name",
		):
			frappe.delete_doc("MoE Return Submission", name, force=True, ignore_permissions=True)

	def test_auto_generate_creates_single_draft(self):
		if not frappe.db.exists("MoE Return Template", "EMIS-001"):
			self.skipTest("EMIS-001 template not seeded (after_install not run in this environment)")

		auto_generate_monthly_enrolment_return()

		reporting_period = formatdate(today(), "MMMM yyyy")
		subs = frappe.get_all(
			"MoE Return Submission",
			filters={"template": "EMIS-001", "reporting_period": reporting_period},
		)
		self.assertEqual(len(subs), 1)
		self.assertNotIn("template_code", subs[0].name)

	def test_auto_generate_is_idempotent(self):
		if not frappe.db.exists("MoE Return Template", "EMIS-001"):
			self.skipTest("EMIS-001 template not seeded (after_install not run in this environment)")

		auto_generate_monthly_enrolment_return()
		auto_generate_monthly_enrolment_return()

		reporting_period = formatdate(today(), "MMMM yyyy")
		subs = frappe.get_all(
			"MoE Return Submission",
			filters={"template": "EMIS-001", "reporting_period": reporting_period},
		)
		self.assertEqual(len(subs), 1)

	def test_check_upcoming_deadlines_does_not_raise(self):
		check_upcoming_deadlines()

	def test_generate_daily_attendance_snapshot_does_not_raise(self):
		generate_daily_attendance_snapshot()

	def tearDown(self):
		frappe.db.rollback()
