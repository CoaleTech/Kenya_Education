"""A8 guardian operations tests. Integration cases belong on an isolated CI site, never a live school site."""

from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime

from frappe_education_kenya import messaging, parent_ops, portal
from frappe_education_kenya.frappe_education_kenya.report.guardian_consent_coverage.guardian_consent_coverage import (
	execute,
)


class TestGuardianContracts(TestCase):
	def test_latest_messaging_decision_wins(self):
		with patch.object(frappe, "get_all", return_value=[frappe._dict(status="Revoked")]) as get_all:
			self.assertFalse(parent_ops.has_messaging_consent("g1", "s1"))
		self.assertEqual(get_all.call_args.kwargs["limit_page_length"], 1)
		self.assertTrue(get_all.call_args.kwargs["order_by"].startswith("captured_on desc"))
		with patch.object(frappe, "get_all", return_value=[frappe._dict(status="Granted")]):
			self.assertTrue(parent_ops.has_messaging_consent("g1", "s1"))
		with patch.object(frappe, "get_all", return_value=[]):
			self.assertFalse(parent_ops.has_messaging_consent("g1", "s1"))
		self.assertFalse(parent_ops.has_messaging_consent(None, "s1"))

	def test_linked_students_merges_own_and_ward_records(self):
		with (
			patch.object(parent_ops, "get_guardians_for_user", return_value=["G1"]),
			patch.object(frappe, "get_all", side_effect=[["S2", "S1"], ["S1", "S3"]]),
		):
			self.assertEqual(parent_ops.linked_students("u@example.com"), ["S1", "S2", "S3"])
		self.assertEqual(parent_ops.linked_students("Guest"), [])

	def test_audience_filters_reject_unexpected_shapes(self):
		for audience, raw in (
			("Class", "[]"),
			("Class", "{bad"),
			("Class", {"student_group": "x", "extra": 1}),
			("Fees Balance", {"minimum_balance": True}),
			("Fees Balance", {"minimum_balance": -1}),
			("Fees Balance", {"minimum_balance": float("inf")}),
			("Guardian List", {"guardians": []}),
			("Guardian List", {"guardians": [1]}),
			("Everyone", {}),
		):
			with self.subTest(audience=audience, raw=raw), self.assertRaises(frappe.ValidationError):
				messaging.validated_filters(audience, raw)

	def test_pagination_is_bounded(self):
		self.assertEqual(portal.pagination("5", "20"), (5, 20))
		for start, limit in ((-1, 20), (0, 0), (0, 101), (True, 20), ("x", 20)):
			with self.subTest(start=start, limit=limit), self.assertRaises(frappe.ValidationError):
				portal.pagination(start, limit)

	def test_consent_is_read_per_recipient_immediately_before_send(self):
		rows = [
			frappe._dict(guardian="g1", student="s1", result="Pending"),
			frappe._dict(guardian="g2", student="s2", result="Pending"),
		]
		doc = MagicMock(
			status="Scheduled", send_at=now_datetime(), recipients=rows, body="Hello", flags=frappe._dict()
		)
		calls = []

		def consent(guardian, student):
			calls.append(("consent", guardian))
			return guardian == "g1"

		def send(numbers, *args, **kwargs):
			calls.append(("send", numbers[0]))

		with (
			patch.object(messaging, "dispatch_enabled", return_value=True),
			patch.object(frappe, "only_for"),
			patch.object(frappe, "has_permission"),
			patch.object(frappe, "qb", MagicMock()),
			patch.object(frappe, "get_doc", return_value=doc),
			patch.object(frappe.db, "get_value", side_effect=lambda dt, name, field: f"07{name}"),
			patch.object(frappe.db, "get_single_value", return_value="https://gateway.invalid"),
			patch.object(messaging, "guardian_student_link", return_value=True),
			patch.object(messaging, "has_messaging_consent", side_effect=consent),
			patch.object(messaging, "send_sms", side_effect=send),
		):
			messaging.dispatch_message("msg")
		self.assertEqual(calls, [("consent", "g1"), ("send", "07g1"), ("consent", "g2")])
		self.assertEqual([r.result for r in rows], ["Submitted to gateway", "Skipped: no active consent"])
		self.assertEqual(doc.status, "Sent")

	def test_dispatch_is_inert_until_enabled(self):
		with (
			patch.object(messaging, "dispatch_enabled", return_value=False),
			patch.object(frappe, "get_doc") as get_doc,
		):
			messaging.dispatch_message("msg")
			messaging.dispatch_due()
		get_doc.assert_not_called()


class TestGuardianOperations(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		with self.set_user("Administrator"):
			parent_ops.setup()
			self.prefix = f"_Test A8 {frappe.generate_hash(length=10)}"
			self.guardian_user = self.make_user("guardian", "Guardian")
			self.other_user = self.make_user("other", "Guardian")
			self.bursar = self.make_user("bursar", "Bursar")
			self.guardian = self.make_guardian(self.guardian_user)
			self.other_guardian = self.make_guardian(self.other_user)
			self.student = self.make_student(self.guardian)
			self.other_student = self.make_student(self.other_guardian)

	def make_user(self, label, role):
		return (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"a8-{label}-{frappe.generate_hash(length=10)}@example.com",
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
					"mobile_number": "+254700000000",
				}
			)
			.insert()
			.name
		)

	def make_student(self, guardian):
		return (
			frappe.get_doc(
				{
					"doctype": "Student",
					"first_name": self.prefix,
					"last_name": frappe.generate_hash(length=6),
					"student_email_id": f"a8-student-{frappe.generate_hash(length=10)}@example.com",
					"naming_series": "EDU-STU-.YYYY.-",
					"guardians": [{"guardian": guardian, "guardian_name": guardian, "relation": "Others"}],
				}
			)
			.insert()
			.name
		)

	def test_portal_consent_is_append_only_and_linked(self):
		with self.set_user(self.guardian_user):
			first = portal.set_consent(self.student, "Messaging", True)["name"]
			self.assertTrue(parent_ops.has_messaging_consent(self.guardian, self.student))
			portal.set_consent(self.student, "Messaging", False)
			self.assertFalse(parent_ops.has_messaging_consent(self.guardian, self.student))
			doc = frappe.get_doc("Guardian Consent", first)
			doc.status = "Revoked"
			self.assertRaises(frappe.ValidationError, doc.save)
			self.assertRaises(
				frappe.PermissionError, portal.set_consent, self.other_student, "Messaging", True
			)
			self.assertRaises(frappe.ValidationError, portal.set_consent, self.student, "Marketing", True)
			self.assertRaises(
				frappe.PermissionError,
				frappe.get_doc(
					{
						"doctype": "Guardian Consent",
						"guardian": self.other_guardian,
						"student": self.other_student,
						"purpose": "Photo",
						"status": "Granted",
						"captured_via": "Portal",
					}
				).insert,
			)
			self.assertEqual(frappe.get_list("Guardian Consent", filters={"student": self.other_student}), [])

	def test_portal_reads_require_linkage_and_publication(self):
		with self.set_user(self.other_user):
			for method in (
				portal.fee_statement,
				portal.pledges,
				portal.library_items,
				portal.timetable,
				portal.results,
			):
				with self.subTest(method=method.__name__):
					self.assertRaises(frappe.PermissionError, method, self.student)
		with self.set_user(self.guardian_user):
			self.assertEqual(portal.results(self.student)["data"], [])
			self.assertEqual([c.name for c in portal.linked_children()], [self.student])
		with self.set_user("Guest"):
			self.assertRaises(frappe.PermissionError, portal.fee_statement, self.student)

	def test_publication_flag_is_staff_only(self):
		doc = frappe._dict(kenya_guardian_published=1, get_doc_before_save=lambda: None)
		with self.set_user(self.guardian_user):
			self.assertRaises(frappe.PermissionError, parent_ops.validate_result_publication, doc)

	def test_schedule_snapshots_audience_without_sending(self):
		with self.set_user(self.bursar):
			doc = frappe.get_doc(
				{
					"doctype": "Scheduled Message",
					"audience": "Guardian List",
					"filters": frappe.as_json({"guardians": [self.guardian]}),
					"body": "Term opens Monday",
					"send_at": add_days(now_datetime(), 1),
				}
			).insert()
			with patch.object(messaging, "send_sms") as send:
				messaging.schedule(doc.name)
			doc.reload()
			self.assertEqual(doc.status, "Scheduled")
			self.assertEqual(
				[(r.guardian, r.student, r.result) for r in doc.recipients],
				[(self.guardian, self.student, "Pending")],
			)
			send.assert_not_called()
			doc.body = "Changed"
			self.assertRaises(frappe.ValidationError, doc.save)
			self.assertRaises(
				frappe.ValidationError,
				frappe.get_doc(
					{
						"doctype": "Scheduled Message",
						"audience": "Class",
						"filters": "{}",
						"body": "x",
						"send_at": add_days(now_datetime(), 1),
					}
				).insert,
			)
		with self.set_user(self.guardian_user):
			self.assertRaises(frappe.PermissionError, messaging.schedule, doc.name)

	def test_login_audit_is_hook_only(self):
		parent_ops.on_session_creation(frappe._dict(user=self.guardian_user))
		self.assertTrue(
			frappe.db.exists("Parent Login Log", {"guardian": self.guardian, "user": self.guardian_user})
		)
		self.assertRaises(
			frappe.PermissionError,
			frappe.get_doc(
				{
					"doctype": "Parent Login Log",
					"guardian": self.guardian,
					"user": self.guardian_user,
					"logged_in_at": now_datetime(),
				}
			).insert,
		)

	def test_coverage_report_shows_missing_and_latest(self):
		with self.set_user(self.guardian_user):
			portal.set_consent(self.student, "Messaging", True)
		with self.set_user(self.bursar):
			_columns, data = execute({"student": self.student})
			status = {row["purpose"]: row["status"] for row in data}
			self.assertEqual(status["Messaging"], "Granted")
			self.assertEqual(status["Photo"], "Missing")
			self.assertRaises(frappe.ValidationError, execute, {"purpose": "Marketing"})
		with self.set_user(self.guardian_user):
			self.assertRaises(frappe.PermissionError, execute, {})
