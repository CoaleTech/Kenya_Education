"""A4 integration tests for an isolated test site; every test rolls back its records."""

from datetime import timedelta

import frappe
from frappe.model.workflow import WorkflowTransitionError, apply_workflow
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime

from frappe_education_kenya import teaching

STUDENT = "edk-exam-student@example.com"
GUARDIAN = "edk-exam-guardian@example.com"
INSTRUCTOR = "edk-exam-instructor@example.com"
OTHER = "edk-exam-other@example.com"
ADMIN = "edk-exam-admin@example.com"
HEAD = "edk-exam-head@example.com"


def make_user(email, *roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
				"roles": [{"role": role} for role in roles],
			}
		).insert(ignore_permissions=True)
	return email


def make_instructor(user):
	company = frappe.db.get_value("Company", {}, "name")
	employee = frappe.get_doc(
		{
			"doctype": "Employee",
			"first_name": user.split("@")[0],
			"gender": "Male",
			"company": company,
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2020-01-01",
			"user_id": user,
			"create_user_permission": 0,
		}
	).insert(ignore_permissions=True)
	return (
		frappe.get_doc(
			{
				"doctype": "Instructor",
				"instructor_name": employee.first_name,
				"employee": employee.name,
				"naming_series": "EDU-INS-.YYYY.-",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def make_academics():
	year = frappe.get_doc(
		{
			"doctype": "Academic Year",
			"academic_year_name": "EDK A4 2099",
			"year_start_date": "2099-01-01",
			"year_end_date": "2099-12-31",
		}
	).insert(ignore_permissions=True)
	term = frappe.get_doc(
		{
			"doctype": "Academic Term",
			"academic_year": year.name,
			"term_name": "A4 T1",
			"term_start_date": "2099-01-01",
			"term_end_date": "2099-04-30",
		}
	).insert(ignore_permissions=True)
	course = frappe.get_doc({"doctype": "Course", "course_name": "EDK A4 Science"}).insert(
		ignore_permissions=True
	)
	group = frappe.get_doc(
		{
			"doctype": "Student Group",
			"academic_year": year.name,
			"group_based_on": "Activity",
			"student_group_name": "EDK A4 Group",
		}
	).insert(ignore_permissions=True)
	return frappe._dict(year=year.name, term=term.name, course=course.name, group=group.name)


class TeachingIntegration(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		teaching.setup()
		make_user(STUDENT, "Student")
		make_user(GUARDIAN, "Guardian")
		make_user(INSTRUCTOR, "Instructor")
		make_user(OTHER, "Instructor")
		make_user(ADMIN, "Academic Admin")
		make_user(HEAD, "Head Teacher")
		# Core Instructor naming needs this site setting; the value rolls back with the test.
		frappe.db.set_single_value("Education Settings", "instructor_created_by", "Full Name")
		self.instructor = make_instructor(INSTRUCTOR)
		self.other_instructor = make_instructor(OTHER)
		self.academics = make_academics()

	def act(self, user, doc, action):
		frappe.set_user(user)
		try:
			return apply_workflow(frappe.get_doc(doc.doctype, doc.name), action)
		finally:
			frappe.set_user("Administrator")


class TestExamPaper(TeachingIntegration):
	def make_paper(self):
		question = frappe.get_doc(
			{
				"doctype": "Question",
				"question": "<p>What is 2 + 2?</p>",
				"options": [{"option": "4", "is_correct": 1}, {"option": "5", "is_correct": 0}],
			}
		).insert(ignore_permissions=True)
		frappe.set_user(INSTRUCTOR)
		doc = frappe.get_doc(
			{
				"doctype": "Exam Paper",
				"title": "A4 Science",
				"instructor": self.instructor,
				"course": self.academics.course,
				"student_group": self.academics.group,
				"exam_date": "2099-03-01",
				"duration_minutes": 60,
				"release_on": now_datetime() + timedelta(days=1),
				"items": [{"question": question.name, "marks": 5, "section": "A"}],
			}
		).insert()
		attachment = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "a4-paper.txt",
				"content": b"confidential",
				"attached_to_doctype": "Exam Paper",
				"attached_to_name": doc.name,
				"is_private": 0,
			}
		).insert()
		frappe.set_user("Administrator")
		self.act(INSTRUCTOR, doc, "Submit for Review")
		self.act(ADMIN, doc, "Approve")
		return self.act(ADMIN, doc, "Lock"), question, attachment

	def assert_hidden(self, user, doc, attachment):
		self.assertFalse(frappe.has_permission("Exam Paper", "read", doc=doc, user=user))
		self.assertFalse(frappe.has_permission("Exam Paper", "print", doc=doc, user=user))
		self.assertFalse(frappe.has_permission("File", "read", doc=attachment, user=user))
		frappe.set_user(user)
		try:
			self.assertFalse(frappe.get_list("Exam Paper", filters={"name": doc.name}))
			self.assertFalse(frappe.get_list("File", filters={"name": attachment.name}))
			self.assertFalse(frappe.get_doc("File", attachment.name).is_downloadable())
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("File", attachment.name).get_content()
		finally:
			frappe.set_user("Administrator")

	def test_student_and_guardian_denied_before_release(self):
		doc, _question, attachment = self.make_paper()
		attachment.reload()
		self.assertEqual(attachment.is_private, 1)
		self.assertTrue(attachment.file_url.startswith("/private/files/"))
		for user in (STUDENT, GUARDIAN, OTHER):
			self.assert_hidden(user, doc, attachment)
		with self.assertRaises(WorkflowTransitionError):
			self.act("Administrator", doc, "Release")
		frappe.db.set_value("Exam Paper", doc.name, "release_on", now_datetime() - timedelta(minutes=1))
		self.act("Administrator", doc, "Release")
		self.assertTrue(frappe.has_permission("Exam Paper", "read", doc=doc.name, user=STUDENT))
		self.assertTrue(frappe.has_permission("File", "read", doc=attachment.name, user=GUARDIAN))

	def test_locked_paper_read_only(self):
		doc, question, attachment = self.make_paper()
		self.assertFalse(frappe.has_permission("Exam Paper", "write", doc=doc, user=ADMIN))
		doc = frappe.get_doc("Exam Paper", doc.name)
		doc.title = "Changed"
		with self.assertRaises(frappe.ValidationError):
			doc.save()
		question.reload()
		question.question = "<p>Changed</p>"
		with self.assertRaises(frappe.ValidationError):
			question.save()
		with self.assertRaises((frappe.PermissionError, frappe.ValidationError)):
			frappe.delete_doc("File", attachment.name)
		self.assertIn("What is 2 + 2?", frappe.get_print("Exam Paper", doc.name, "Exam Paper (Locked)"))

	def test_other_instructor_cannot_reuse_confidential_question(self):
		_doc, question, _attachment = self.make_paper()
		self.assertFalse(frappe.has_permission("Question", "read", doc=question.name, user=OTHER))
		frappe.set_user(OTHER)
		try:
			self.assertFalse(frappe.get_list("Question", filters={"name": question.name}))
		finally:
			frappe.set_user("Administrator")


class TestTeachingWorkflows(TeachingIntegration):
	def make_scheme(self):
		frappe.set_user(INSTRUCTOR)
		try:
			return frappe.get_doc(
				{
					"doctype": "Scheme of Work",
					"instructor": self.instructor,
					"course": self.academics.course,
					"academic_term": self.academics.term,
					"weeks": [
						{"week_no": 1, "strand": "Living Things", "outcomes": "<p>Classify plants</p>"}
					],
				}
			).insert()
		finally:
			frappe.set_user("Administrator")

	def test_scheme_and_lesson_plan_happy_and_role_denied(self):
		scheme = self.make_scheme()
		self.assertFalse(frappe.has_permission("Scheme of Work", "read", doc=scheme.name, user=OTHER))
		self.act(INSTRUCTOR, scheme, "Submit for Approval")
		with self.assertRaises(WorkflowTransitionError):
			self.act(ADMIN, scheme, "Approve")
		with self.assertRaises(WorkflowTransitionError):
			self.act(INSTRUCTOR, scheme, "Approve")
		self.assertEqual(self.act(HEAD, scheme, "Approve").workflow_state, "Approved")

		scheme.reload()
		frappe.set_user(INSTRUCTOR)
		try:
			lesson = frappe.get_doc(
				{
					"doctype": "Lesson Plan",
					"instructor": self.instructor,
					"course": self.academics.course,
					"lesson_date": "2099-01-10",
					"scheme_of_work": scheme.name,
					"scheme_week": scheme.weeks[0].name,
					"objectives": "<p>Classify plants</p>",
					"activities": "<p>Field walk</p>",
				}
			).insert()
		finally:
			frappe.set_user("Administrator")
		self.act(INSTRUCTOR, lesson, "Submit for Approval")
		with self.assertRaises(WorkflowTransitionError):
			self.act(HEAD, lesson, "Approve")
		self.assertEqual(self.act(ADMIN, lesson, "Return").workflow_state, "Returned")
		self.act(INSTRUCTOR, lesson, "Submit for Approval")
		self.assertEqual(self.act(ADMIN, lesson, "Approve").workflow_state, "Approved")

		lesson = frappe.get_doc("Lesson Plan", lesson.name)
		lesson.reflection = "<p>Edited after approval</p>"
		with self.assertRaises(frappe.ValidationError):
			lesson.save()
