"""A9 contract tests. Integration cases belong on an isolated CI site, never a live school site."""

from unittest import TestCase
from unittest.mock import patch

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase

from frappe_education_kenya import pathways
from frappe_education_kenya.frappe_education_kenya.report.pathway_placement_by_combination.pathway_placement_by_combination import (
	execute,
)


class TestPathwayConsentDecision(TestCase):
	def test_revocation_wins_over_older_grant_for_same_guardian(self):
		rows = [
			frappe._dict(name="revoked", guardian="g1", status="Revoked"),
			frappe._dict(name="old-grant", guardian="g1", status="Granted"),
		]
		with patch.object(frappe, "get_all", side_effect=[["g1"], rows]):
			self.assertIsNone(pathways.active_guardian_consent("s1"))

	def test_another_linked_guardian_can_give_active_consent(self):
		rows = [
			frappe._dict(name="revoked", guardian="g1", status="Revoked"),
			frappe._dict(name="grant", guardian="g2", status="Granted"),
		]
		with patch.object(frappe, "get_all", side_effect=[["g1", "g2"], rows]):
			self.assertEqual(pathways.active_guardian_consent("s1"), "grant")

	def test_no_guardian_link_never_grants_consent(self):
		with patch.object(frappe, "get_all", return_value=[]):
			self.assertIsNone(pathways.active_guardian_consent("s1"))


class TestPathways(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		with self.set_user("Administrator"):
			pathways.setup()
			self.prefix = f"_Test CBC {frappe.generate_hash(length=10)}"
			self.year = (
				frappe.get_doc(
					{
						"doctype": "Academic Year",
						"academic_year_name": self.prefix,
						"year_start_date": "2026-01-01",
						"year_end_date": "2026-12-31",
					}
				)
				.insert()
				.name
			)
			frappe.db.set_single_value("Education Settings", "current_academic_year", self.year)
			self.guardian_user = self.make_user("guardian", "Guardian")
			self.student_user = self.make_user("student", "Student")
			self.academic_user = self.make_user("academic", "Academic Admin")
			self.head_user = self.make_user("head", "Head Teacher")
			self.other_guardian_user = self.make_user("other", "Guardian")
			self.guardian = self.make_guardian(self.guardian_user)
			self.other_guardian = self.make_guardian(self.other_guardian_user)
			self.student = self.make_student(self.student_user, self.guardian)
			self.other_student = self.make_student(None, self.other_guardian)
			self.course = frappe.get_doc({"doctype": "Course", "course_name": self.prefix}).insert().name
			self.pathway = (
				frappe.get_doc(
					{
						"doctype": "CBC Pathway",
						"pathway_name": self.prefix,
						"tracks": [{"track_name": "School Confirmed", "is_confirmed": 1}],
					}
				)
				.insert()
				.name
			)
			self.combination = self.make_combination("First", 1)
			self.second = self.make_combination("Second", 2)
			self.consent(self.student, self.guardian)
			self.consent(self.other_student, self.other_guardian)

	def make_user(self, label, role):
		email = f"cbc-{label}-{frappe.generate_hash(length=10)}@example.com"
		return (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": label,
					"send_welcome_email": 0,
					"roles": [{"role": role}],
				}
			)
			.insert()
			.name
		)

	def make_guardian(self, user):
		return (
			frappe.get_doc(
				{
					"doctype": "Guardian",
					"guardian_name": user,
					"email_address": user,
					"user": user,
				}
			)
			.insert()
			.name
		)

	def make_student(self, user, guardian):
		email = user or f"cbc-other-{frappe.generate_hash(length=10)}@example.com"
		if not user:
			user = (
				frappe.get_doc(
					{
						"doctype": "User",
						"email": email,
						"first_name": "CBC Other Student",
						"send_welcome_email": 0,
						"roles": [{"role": "Student"}],
					}
				)
				.insert()
				.name
			)
		return (
			frappe.get_doc(
				{
					"doctype": "Student",
					"first_name": self.prefix,
					"last_name": frappe.generate_hash(length=6),
					"student_email_id": email,
					"user": user,
					"naming_series": "EDU-STU-.YYYY.-",
					"kenya_kjsea_score": 340,
					"guardians": [{"guardian": guardian, "guardian_name": guardian, "relation": "Others"}],
				}
			)
			.insert()
			.name
		)

	def make_combination(self, label, capacity):
		return (
			frappe.get_doc(
				{
					"doctype": pathways.COMBINATION,
					"combination_name": f"{self.prefix} {label}",
					"pathway": self.pathway,
					"track": "School Confirmed",
					"capacity": capacity,
					"enabled": 1,
					"subjects": [{"course": self.course, "kind": "Core"}],
				}
			)
			.insert()
			.name
		)

	def consent(self, student, guardian, status="Granted"):
		with self.set_user("Administrator"):
			return (
				frappe.get_doc(
					{
						"doctype": "Guardian Consent",
						"student": student,
						"guardian": guardian,
						"purpose": "Data Sharing",
						"status": status,
						"captured_via": "Paper",
					}
				)
				.insert()
				.name
			)

	def choose(self, student=None, user=None):
		with self.set_user(user or self.guardian_user):
			result = pathways.choose_pathway(
				student or self.student, self.combination, self.second, "Interests"
			)
			return frappe.get_doc(pathways.CHOICE, result["name"])

	def transition(self, doc, action, user):
		with self.set_user(user):
			apply_workflow(doc, action)
		return frappe.get_doc(pathways.CHOICE, doc.name)

	def approved_choice(self, student=None, user=None):
		doc = self.choose(student, user)
		doc = self.transition(doc, "Submit Choice", user or self.guardian_user)
		return self.transition(doc, "Approve", self.academic_user)

	def prepare_placement(self, doc, *, user=None, reason=None):
		with self.set_user(user or self.academic_user):
			doc = frappe.get_doc(pathways.CHOICE, doc.name)
			doc.placement = self.combination
			if reason is not None:
				doc.override_reason = reason
			doc.save()
		return doc

	def test_one_choice_per_student_year(self):
		doc = self.choose()
		self.assertEqual(self.choose().name, doc.name)
		with self.set_user(self.guardian_user), self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": pathways.CHOICE,
					"student": self.student,
					"academic_year": self.year,
					"first_choice": self.combination,
				}
			).insert()

	def test_rejected_choice_can_be_replaced_but_cannot_then_override_new_active_choice(self):
		doc = self.choose()
		doc = self.transition(doc, "Submit Choice", self.guardian_user)
		doc = self.transition(doc, "Reject", self.academic_user)
		replacement = self.choose()
		self.assertNotEqual(replacement.name, doc.name)
		doc = self.prepare_placement(doc, user=self.head_user, reason="Review corrected")
		with self.assertRaises(frappe.ValidationError):
			self.transition(doc, "Override Place", self.head_user)

	def test_capacity_enforced(self):
		first = self.prepare_placement(self.approved_choice())
		self.transition(first, "Place", self.academic_user)
		second = self.prepare_placement(self.approved_choice(self.other_student, self.other_guardian_user))
		with self.assertRaises(frappe.ValidationError):
			self.transition(second, "Place", self.academic_user)

	def test_override_requires_reason(self):
		doc = self.prepare_placement(self.approved_choice())
		with self.assertRaises(frappe.PermissionError):
			self.transition(doc, "Override Place", self.head_user)
		doc = frappe.get_doc(pathways.CHOICE, doc.name)  # the denied transition touched the row
		with self.set_user(self.academic_user):
			doc.override_reason = "Not the Head Teacher"
			doc.save()
		self.assertFalse(frappe.db.get_value(pathways.CHOICE, doc.name, "override_reason"))

	def test_head_teacher_override_transition(self):
		first = self.prepare_placement(self.approved_choice())
		self.transition(first, "Place", self.academic_user)
		second = self.approved_choice(self.other_student, self.other_guardian_user)
		second = self.prepare_placement(second, user=self.head_user, reason="Additional supervised place")
		second = self.transition(second, "Override Place", self.head_user)
		self.assertEqual(second.workflow_state, "Placed")
		self.assertEqual(second.override_by, self.head_user)
		self.assertEqual(second.override_reason, "Additional supervised place")
		with self.set_user(self.head_user), self.assertRaises(frappe.PermissionError):
			second.placement = self.second
			second.save()

	def test_workflow_role_denied(self):
		doc = self.transition(self.choose(), "Submit Choice", self.guardian_user)
		with self.assertRaises(frappe.ValidationError):
			self.transition(doc, "Approve", self.guardian_user)
		with self.assertRaises(frappe.ValidationError):
			self.transition(doc, "Approve", self.head_user)
		with self.set_user(self.guardian_user), self.assertRaises(frappe.PermissionError):
			doc.rationale = "Changed after submit"
			doc.save()

	def test_direct_placed_insert_and_guardian_approval_are_denied(self):
		with self.set_user(self.guardian_user), self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": pathways.CHOICE,
					"student": self.student,
					"academic_year": self.year,
					"first_choice": self.combination,
					"placement": self.combination,
					"workflow_state": "Placed",
				}
			).insert()
		doc = self.choose()
		with self.set_user(self.guardian_user), self.assertRaises(frappe.PermissionError):
			doc.workflow_state = "Approved"
			doc.save()

	def test_checkbox_without_active_linked_consent_cannot_submit(self):
		self.consent(self.student, self.guardian, "Revoked")
		doc = self.choose()
		with self.set_user(self.guardian_user):
			doc.guardian_consent = 1
			doc.save()
			self.assertFalse(doc.guardian_consent)
		with self.assertRaises(frappe.ValidationError):
			self.transition(doc, "Submit Choice", self.guardian_user)

	def test_revocation_also_prevents_placement(self):
		doc = self.prepare_placement(self.approved_choice())
		self.consent(self.student, self.guardian, "Revoked")
		with self.assertRaises(frappe.ValidationError):
			self.transition(doc, "Place", self.academic_user)

	def test_guardian_idor_and_list_isolation(self):
		own = self.choose()
		other = self.choose(self.other_student, self.other_guardian_user)
		with self.set_user(self.guardian_user):
			with self.assertRaises(frappe.PermissionError):
				pathways.choose_pathway(self.other_student, self.combination)
			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc(pathways.CHOICE, other.name).check_permission("read")
			visible = frappe.get_list(pathways.CHOICE, pluck="name")
			self.assertIn(own.name, visible)
			self.assertNotIn(other.name, visible)

	def test_student_owns_only_their_choice(self):
		with self.set_user(self.student_user):
			result = pathways.choose_pathway(self.student, self.combination)
			self.assertTrue(result["ok"])
			with self.assertRaises(frappe.PermissionError):
				pathways.choose_pathway(self.other_student, self.combination)

	def test_kjsea_basis_is_server_derived_and_frozen_on_submit(self):
		doc = self.choose()
		with self.set_user(self.guardian_user):
			doc.kjsea_basis = 500
			doc.save()
		self.assertEqual(frappe.db.get_value(pathways.CHOICE, doc.name, "kjsea_basis"), 340)
		doc = self.transition(doc, "Submit Choice", self.guardian_user)
		with self.set_user(self.academic_user), self.assertRaises(frappe.PermissionError):
			doc.kjsea_basis = 500
			doc.save()

	def test_combination_requires_valid_confirmed_track_and_distinct_subjects(self):
		with self.set_user("Administrator"):
			doc = frappe.get_doc(pathways.COMBINATION, self.combination)
			doc.track = "Not a pathway track"
			with self.assertRaises(frappe.ValidationError):
				doc.save()
			doc.reload()
			doc.append("subjects", {"course": self.course, "kind": "Elective"})
			with self.assertRaises(frappe.ValidationError):
				doc.save()
			pathway = frappe.get_doc("CBC Pathway", self.pathway)
			pathway.append("tracks", {"track_name": "Editable Draft", "is_confirmed": 0})
			pathway.save()
			doc.reload()
			doc.track = "Editable Draft"
			with self.assertRaises(frappe.ValidationError):
				doc.save()

	def test_report_uses_placed_records_for_selected_year(self):
		doc = self.prepare_placement(self.approved_choice())
		self.transition(doc, "Place", self.academic_user)
		with self.set_user(self.academic_user):
			columns, rows = execute({"academic_year": self.year, "combination": self.combination})
			self.assertEqual(len(rows), 1)
			self.assertEqual(rows[0].placed, 1)
			self.assertEqual(rows[0].remaining, 0)
			self.assertNotIn("kjsea_basis", {column["fieldname"] for column in columns})
		with self.set_user(self.guardian_user), self.assertRaises(frappe.PermissionError):
			execute({"academic_year": self.year})
