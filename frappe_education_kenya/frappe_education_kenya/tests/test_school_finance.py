"""No-DB regression coverage for bursary, pledge and collection-inbox rules."""

from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from frappe_education_kenya import bursary, collections


def row(**values):
	return frappe._dict(values)


class TestSchoolFinance(TestCase):
	def setUp(self):
		# Isolate framework message logging/translation, not finance decisions.
		def fail(message, exc=frappe.ValidationError, **kwargs):
			raise exc(message)

		self.addCleanup(patch.stopall)
		patch.object(frappe, "throw", side_effect=fail).start()
		for module in (bursary, collections):
			patch.object(module, "_", side_effect=lambda message: message).start()

	def test_money_rejects_unsafe_amounts(self):
		self.assertEqual(bursary.money("10.50"), Decimal("10.50"))
		for value in ("NaN", "Infinity", 0, -1, "1.001", None, {}):
			with self.subTest(value=value), self.assertRaises(frappe.ValidationError):
				bursary.money(value)

	def award(self, **values):
		doc = MagicMock(
			workflow_state="Approved",
			valid_from="2026-01-01",
			valid_to="2026-12-31",
			amount=1000,
			allocations=[],
			student="ADM-1",
			pledge=None,
		)
		doc.configure_mock(**values)
		return doc

	def test_allocation_retry_is_idempotent(self):
		doc = self.award(
			allocations=[
				row(reference_doctype="Fees", reference_name="FEE-1", amount=400, payment_entry="PE-1")
			]
		)
		with (
			patch.object(bursary, "gate"),
			patch.object(bursary, "nowdate", return_value="2026-11-10"),
			patch.object(frappe, "get_doc", return_value=doc),
			patch.object(frappe, "db", MagicMock(**{"get_value.return_value": 0})),
			patch.object(bursary, "make_payment") as make,
		):
			self.assertEqual(bursary.allocate("AW-1", "FEE-1", 400, "Fees")["name"], "PE-1")
			with self.assertRaises(frappe.ValidationError):
				bursary.allocate("AW-1", "FEE-1", 300, "Fees")
		make.assert_not_called()

	def test_over_allocation_rejected_before_payment(self):
		doc = self.award(
			allocations=[
				row(reference_doctype="Fees", reference_name="FEE-1", amount=900, payment_entry="PE-1")
			]
		)
		with (
			patch.object(bursary, "gate"),
			patch.object(bursary, "nowdate", return_value="2026-11-10"),
			patch.object(frappe, "get_doc", return_value=doc),
			patch.object(frappe, "db", MagicMock(**{"get_value.return_value": 1})),
			patch.object(bursary, "make_payment") as make,
			self.assertRaises(frappe.ValidationError),
		):
			bursary.allocate("AW-1", "SINV-1", 200)
		make.assert_not_called()

	def test_unapproved_award_cannot_allocate(self):
		with (
			patch.object(bursary, "gate"),
			patch.object(frappe, "get_doc", return_value=self.award(workflow_state="Pending Approval")),
			self.assertRaises(frappe.ValidationError),
		):
			bursary.allocate("AW-1", "SINV-1", 100)

	def test_cancelled_reservation_not_counted(self):
		rows = [
			row(amount=100, payment_entry="PE-1"),
			row(amount=200, payment_entry="PE-2"),
			row(amount=50, payment_entry=None),
		]
		with patch.object(frappe, "db", MagicMock(**{"get_value.side_effect": [1, 2]})):
			self.assertEqual(bursary.allocation_total(rows), Decimal(100))

	def test_posted_collection_payment_cannot_cancel(self):
		with self.assertRaises(frappe.ValidationError):
			bursary.payment_rollup(frappe._dict(electronic_collection="EC-1"), "on_cancel")

	def test_match_requires_exact_student_id(self):
		doc = MagicMock(status="New", account_reference="adm-1")
		with (
			patch.object(collections, "gate"),
			patch.object(frappe, "get_doc", return_value=doc),
			patch.object(frappe, "db", MagicMock(**{"get_value.return_value": "ADM-1"})),
		):
			collections.match("EC-1")
		self.assertIsNone(doc.student)
		self.assertEqual(doc.workflow_state, "Needs Review")
		doc.save.assert_called_once()

	def test_final_collection_cannot_rematch(self):
		with (
			patch.object(collections, "gate"),
			patch.object(frappe, "get_doc", return_value=MagicMock(status="Posted")),
			self.assertRaises(frappe.ValidationError),
		):
			collections.match("EC-1")

	def test_guardian_scope(self):
		db = MagicMock(**{"escape.side_effect": lambda value: f"'{value}'"})
		with patch.object(frappe, "db", db), patch.object(frappe, "get_roles", return_value=["Guardian"]):
			with patch.object(bursary, "guardian_students", return_value=[]):
				self.assertEqual(bursary.fee_pledge_query("g@example.com"), "1=0")
			with patch.object(bursary, "guardian_students", return_value=["ADM-1"]):
				self.assertEqual(
					bursary.bursary_award_query("g@example.com"), "`tabBursary Award`.`student` in ('ADM-1')"
				)
				self.assertTrue(
					bursary.guardian_finance_permission(row(student="ADM-1"), "read", "g@example.com")
				)
				self.assertFalse(
					bursary.guardian_finance_permission(row(student="ADM-2"), "read", "g@example.com")
				)
				self.assertFalse(
					bursary.guardian_finance_permission(row(student="ADM-1"), "write", "g@example.com")
				)
		with patch.object(frappe, "get_roles", return_value=["Bursar"]):
			self.assertEqual(bursary.fee_pledge_query("b@example.com"), "")

	def reminder_run(self, consent, settings):
		pledge = MagicMock(
			due_date="2026-11-10", reminder_days_before=3, reminders=[], guardian="G-1", student="ADM-1"
		)
		with (
			patch.object(frappe, "get_single", return_value=frappe._dict(settings)),
			patch.object(frappe, "get_all", return_value=["FP-1"]),
			patch.object(frappe, "get_doc", return_value=pledge),
			patch.object(
				frappe,
				"db",
				MagicMock(
					**{
						"get_value.return_value": "0700000000",
						"get_single_value.return_value": "https://sms.example",
					}
				),
			),
			patch("frappe_education_kenya.parent_ops.has_messaging_consent", return_value=consent),
			patch("frappe.core.doctype.sms_settings.sms_settings.send_sms") as send,
			patch.object(bursary, "nowdate", return_value="2026-11-10"),
			patch.object(bursary, "now_datetime", return_value="2026-11-10 08:00:00"),
		):
			bursary.daily_reminders()
		return pledge, send

	def test_reminder_without_consent_logs_and_never_sends(self):
		pledge, send = self.reminder_run(
			False, {"kenya_enable_pledge_reminders": 1, "kenya_enable_scheduled_messages": 1}
		)
		send.assert_not_called()
		self.assertEqual(pledge.append.call_args.args[1]["result"], "No active consent")

	def test_reminder_needs_both_explicit_settings(self):
		for settings in ({}, {"kenya_enable_pledge_reminders": 1}, {"kenya_enable_scheduled_messages": 1}):
			with self.subTest(settings=settings):
				pledge, send = self.reminder_run(True, settings)
				send.assert_not_called()
				self.assertEqual(pledge.append.call_args.args[1]["result"], "Disabled")
		pledge, send = self.reminder_run(
			True, {"kenya_enable_pledge_reminders": 1, "kenya_enable_scheduled_messages": 1}
		)
		send.assert_called_once()
