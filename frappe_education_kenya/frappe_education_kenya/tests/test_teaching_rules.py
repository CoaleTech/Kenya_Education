"""No-DB A4 rules; safe to run without creating records."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from frappe_education_kenya import teaching

STUDENT = "student@example.com"
GUARDIAN = "guardian@example.com"
INSTRUCTOR = "instructor@example.com"
ADMIN = "admin@example.com"


NOW = datetime(2026, 11, 10, 9)


def paper(**values):
	return frappe._dict(
		{
			"doctype": "Exam Paper",
			"name": "EXAM-1",
			"instructor": "INS-1",
			"workflow_state": "Locked",
			"release_on": NOW + timedelta(days=1),
			**values,
		}
	)


class TestTeachingRules(TestCase):
	def setUp(self):
		self.addCleanup(patch.stopall)
		self.roles = patch.object(frappe, "get_roles").start()
		self.instructors = patch.object(teaching, "instructor_names", return_value=["INS-1"]).start()
		self.db = patch.object(frappe, "db", MagicMock()).start()
		self.state = self.db.get_value
		patch.object(teaching, "_", side_effect=lambda message: message).start()
		patch.object(teaching, "now_datetime", return_value=NOW).start()

	def test_learner_denied_before_release_and_never_writes(self):
		self.roles.return_value = ["Student"]
		self.assertFalse(teaching.preparation_permission(paper(), STUDENT, "read"))
		self.assertFalse(teaching.preparation_permission(paper(), STUDENT, "print"))
		released = paper(workflow_state="Released", release_on=NOW - timedelta(minutes=1))
		self.assertTrue(teaching.preparation_permission(released, STUDENT, "read"))
		self.assertFalse(teaching.preparation_permission(released, STUDENT, "write"))
		self.roles.return_value = ["Guardian", "Academic Admin"]
		self.assertFalse(teaching.preparation_permission(paper(), GUARDIAN, "read"))

	def test_instructor_owns_only_draft_content(self):
		self.roles.return_value = ["Instructor"]
		self.assertFalse(teaching.preparation_permission(paper(instructor="INS-2"), INSTRUCTOR, "read"))
		self.state.return_value = "Draft"
		self.assertTrue(
			teaching.preparation_permission(paper(workflow_state="In Review"), INSTRUCTOR, "write")
		)
		self.state.return_value = "In Review"
		# Saved state, not the in-memory value supplied by a crafted save, controls write access.
		self.assertFalse(teaching.preparation_permission(paper(workflow_state="Draft"), INSTRUCTOR, "write"))

	def test_locked_and_released_writes(self):
		self.roles.return_value = ["Academic Admin"]
		self.state.return_value = "Locked"
		self.assertFalse(teaching.preparation_permission(paper(), ADMIN, "write"))
		self.roles.return_value = ["System Manager"]
		self.assertTrue(teaching.preparation_permission(paper(), "manager@example.com", "write"))
		self.state.return_value = "Released"
		self.assertFalse(teaching.preparation_permission(paper(), "manager@example.com", "write"))

	def test_list_conditions_are_quoted_and_fail_closed(self):
		self.roles.return_value = ["Guardian"]
		condition = teaching.paper_query(GUARDIAN)
		self.assertIn("`tabExam Paper`.`workflow_state`='Released'", condition)
		self.assertIn("`tabExam Paper`.`release_on`<=", condition)
		self.roles.return_value = ["Instructor"]
		self.instructors.return_value = []
		self.assertIn("`tabLesson Plan`.`name` IS NULL", teaching.lesson_query(INSTRUCTOR))

	def test_locked_content_change_rejected(self):
		self.roles.return_value = ["System Manager"]
		old = frappe._dict(paper(), title="Old")
		new = SimpleNamespace(get_doc_before_save=lambda: old, instructor="INS-1", workflow_state="Locked")
		with (
			patch.object(teaching, "_business_values", side_effect=[{"title": "Old"}, {"title": "New"}]),
			patch.object(frappe, "throw", side_effect=frappe.ValidationError),
			patch.object(frappe, "session", SimpleNamespace(user="manager@example.com")),
		):
			with self.assertRaises(frappe.ValidationError):
				teaching.validate_preparation(new)

	def test_question_resource_links_are_collected(self):
		parser = teaching._ResourceLinks()
		parser.feed('<p><img src="/files/leak.png"><a href="/private/files/a.pdf">a</a></p>')
		self.assertEqual(parser.links, ["/files/leak.png", "/private/files/a.pdf"])

	def test_release_job_isolates_failures(self):
		due = NOW - timedelta(minutes=1)
		docs = {
			"EXAM-1": frappe._dict(name="EXAM-1", workflow_state="Locked", release_on=due),
			"EXAM-2": frappe._dict(name="EXAM-2", workflow_state="Locked", release_on=due),
		}
		for doc in docs.values():
			doc.as_dict = doc.copy
		with (
			patch.object(frappe, "get_all", return_value=list(docs)),
			patch.object(frappe, "get_doc", side_effect=lambda doctype, name, **kwargs: docs[name]),
			patch.object(teaching, "apply_workflow", side_effect=[Exception("broken"), None]) as apply,
			patch.object(frappe, "log_error"),
			patch.object(frappe, "set_user"),
			patch.object(frappe, "session", SimpleNamespace(user="Guest")),
		):
			teaching.release_exam_papers()
		self.assertEqual(apply.call_count, 2)
		self.db.rollback.assert_called_once()
		self.db.commit.assert_called_once()
