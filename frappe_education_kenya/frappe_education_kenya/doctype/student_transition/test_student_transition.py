"""Tests for Student Transition auto-creation on Program Enrollment submit."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from education.education.test_utils import create_academic_year, create_student


TEST_PROGRAM_A = "Test CBC Grade 6 Program"
TEST_PROGRAM_B = "Test CBC Grade 7 Program"
TEST_ACADEMIC_YEAR = "2023-2024"
TEST_STUDENT_EMAIL = "kenya.transition.test@example.com"


def _ensure_program(name, cbc_level):
	if frappe.db.exists("Program", name):
		doc = frappe.get_doc("Program", name)
	else:
		doc = frappe.new_doc("Program")
		doc.program_name = name
		doc.insert(ignore_permissions=True)
	if doc.get("cbc_level_mapping") != cbc_level:
		frappe.db.set_value("Program", doc.name, "cbc_level_mapping", cbc_level)
	return doc.name


class TestStudentTransition(FrappeTestCase):
	def setUp(self):
		create_academic_year(academic_year_name=TEST_ACADEMIC_YEAR)
		self.program_a = _ensure_program(TEST_PROGRAM_A, "PRI_G6")
		self.program_b = _ensure_program(TEST_PROGRAM_B, "JSS_G7")
		self.student = create_student(
			first_name="Transition", last_name="Tester", student_email_id=TEST_STUDENT_EMAIL
		)

	def test_transition_created_on_first_enrollment(self):
		pe = frappe.new_doc("Program Enrollment")
		pe.student = self.student.name
		pe.program = self.program_a
		pe.academic_year = TEST_ACADEMIC_YEAR
		pe.enrollment_date = nowdate()
		pe.insert(ignore_permissions=True)
		pe.submit()

		transitions = frappe.get_all(
			"Student Transition",
			filters={"student": self.student.name},
			fields=["name", "transition_type", "from_level", "to_level"],
		)
		self.assertEqual(len(transitions), 1)
		self.assertEqual(transitions[0].to_level, "PRI_G6")
		self.assertEqual(transitions[0].transition_type, "Transfer In")
		self.assertIsNone(transitions[0].from_level)

	def test_no_duplicate_transition_on_repeat_call(self):
		from frappe_education_kenya.frappe_education_kenya.doctype.student_transition.student_transition import (
			after_program_enrollment,
		)

		pe = frappe.new_doc("Program Enrollment")
		pe.student = self.student.name
		pe.program = self.program_a
		pe.academic_year = TEST_ACADEMIC_YEAR
		pe.enrollment_date = nowdate()
		pe.insert(ignore_permissions=True)
		pe.submit()

		# Calling the hook again manually for the same enrollment should not duplicate
		after_program_enrollment(pe)

		transitions = frappe.get_all(
			"Student Transition", filters={"student": self.student.name}
		)
		self.assertEqual(len(transitions), 1)

	def test_second_enrollment_records_progression_from_previous_level(self):
		pe1 = frappe.new_doc("Program Enrollment")
		pe1.student = self.student.name
		pe1.program = self.program_a
		pe1.academic_year = TEST_ACADEMIC_YEAR
		pe1.enrollment_date = nowdate()
		pe1.insert(ignore_permissions=True)
		pe1.submit()

		pe2 = frappe.new_doc("Program Enrollment")
		pe2.student = self.student.name
		pe2.program = self.program_b
		pe2.academic_year = TEST_ACADEMIC_YEAR
		pe2.enrollment_date = add_days(nowdate(), 365)
		pe2.insert(ignore_permissions=True)
		pe2.submit()

		transitions = frappe.get_all(
			"Student Transition",
			filters={"student": self.student.name},
			fields=["to_level", "from_level", "transition_type"],
			order_by="creation asc",
		)
		self.assertEqual(len(transitions), 2)
		second = transitions[1]
		self.assertEqual(second.from_level, "PRI_G6")
		self.assertEqual(second.to_level, "JSS_G7")
		self.assertEqual(second.transition_type, "Automatic Progression")

	def test_program_without_cbc_mapping_creates_no_transition(self):
		unmapped_program = "Test Program No CBC Mapping"
		if not frappe.db.exists("Program", unmapped_program):
			doc = frappe.new_doc("Program")
			doc.program_name = unmapped_program
			doc.insert(ignore_permissions=True)

		pe = frappe.new_doc("Program Enrollment")
		pe.student = self.student.name
		pe.program = unmapped_program
		pe.academic_year = TEST_ACADEMIC_YEAR
		pe.enrollment_date = nowdate()
		pe.insert(ignore_permissions=True)
		pe.submit()

		transitions = frappe.get_all("Student Transition", filters={"student": self.student.name})
		self.assertEqual(len(transitions), 0)

	def tearDown(self):
		frappe.db.rollback()
