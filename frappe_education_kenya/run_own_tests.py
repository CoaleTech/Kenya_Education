"""Standalone test runner for frappe_education_kenya tests.

Bypasses bench's `run-tests` machinery (which eagerly imports every test_*.py
in every installed app, including erpnext's, triggering an unrelated Fiscal
Year bootstrap conflict against this site's real data). Instead this connects
to the site directly and runs only our own TestCase classes.

Usage: bench --site <site> execute frappe_education_kenya.run_own_tests.run
"""

import unittest

import frappe

TEST_MODULES = [
	"frappe_education_kenya.frappe_education_kenya.tests.test_assessment",
	"frappe_education_kenya.frappe_education_kenya.doctype.student_transition.test_student_transition",
	"frappe_education_kenya.frappe_education_kenya.doctype.moe_return_submission.test_moe_return_submission",
	"frappe_education_kenya.frappe_education_kenya.doctype.transport_vehicle.test_transport_vehicle",
	"frappe_education_kenya.frappe_education_kenya.doctype.cbc_fee_settings.test_cbc_fee_settings",
	"frappe_education_kenya.frappe_education_kenya.doctype.cbc_student_settings.test_cbc_student_settings",
]


def run():
	frappe.set_user("Administrator")
	loader = unittest.TestLoader()
	suite = unittest.TestSuite()
	for mod_name in TEST_MODULES:
		mod = __import__(mod_name, fromlist=["*"])
		suite.addTests(loader.loadTestsFromModule(mod))

	runner = unittest.TextTestRunner(verbosity=2)
	result = runner.run(suite)

	print("\n=== SUMMARY ===")
	print(f"Ran: {result.testsRun}")
	print(f"Failures: {len(result.failures)}")
	print(f"Errors: {len(result.errors)}")
	print(f"Skipped: {len(result.skipped)}")

	if not result.wasSuccessful():
		raise SystemExit(1)
