"""No-DB regression coverage for the M-Pesa Paybill ingress and its Payment Channel rules."""

import json
from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import frappe

from frappe_education_kenya import collections
from frappe_education_kenya.frappe_education_kenya.doctype.payment_channel import payment_channel

EAT = ZoneInfo("Africa/Nairobi")


def row(**values):
	return frappe._dict(values)


def trans_time(delta=timedelta()):
	return (datetime.now(EAT) + delta).strftime("%Y%m%d%H%M%S")


def callback(**values):
	return {
		"TransactionType": "Pay Bill",
		"TransID": "UK12345678",
		"TransTime": trans_time(-timedelta(minutes=1)),
		"TransAmount": "1250.00",
		"BusinessShortCode": "174379",
		"BillRefNumber": " ADM-1 ",
		"FirstName": "Jane",
		"MiddleName": "",
		"LastName": "Wanjiku",
		"MSISDN": "2547****1234",
		**values,
	}


class TestPaybillIngress(TestCase):
	def setUp(self):
		def fail(message, exc=frappe.ValidationError, **kwargs):
			raise exc(message)

		self.addCleanup(patch.stopall)
		patch.object(frappe, "throw", side_effect=fail).start()
		patch.object(collections, "_", side_effect=lambda message: message).start()
		patch.object(collections, "paybill_log").start()
		# The real lookup reads System Settings through frappe.db, which is mocked here, so it only
		# passed when an earlier run had warmed the cache.
		patch.object(collections, "get_system_timezone", return_value="UTC").start()
		patch.object(frappe, "session", frappe._dict(user="Guest")).start()
		self.set_user = patch.object(frappe, "set_user").start()
		self.enqueue = patch.object(frappe, "enqueue").start()
		self.get_doc = patch.object(frappe, "get_doc", return_value=MagicMock()).start()
		self.get_doc.return_value.insert.return_value.name = "EC-1"
		self.db = MagicMock(**{"exists.return_value": None})
		patch.object(frappe, "db", self.db).start()
		# Daraja posts JSON, so the URL token is only ever in the query string, never in the payload.
		self.request = patch.object(frappe, "request", MagicMock()).start()

	def channel(self, name="EDK-PC-1", secret="s3cret-token", token="s3cret-token"):
		self.db.get_value.return_value = name
		self.request.args = {"token": token}
		return patch.object(collections, "get_decrypted_password", return_value=secret)

	def test_token_must_match_the_channel_secret(self):
		for name, secret, token in (
			("EDK-PC-1", "s3cret-token", "wrong"),
			("EDK-PC-1", "s3cret-token", ""),
			("EDK-PC-1", None, ""),  # an unset secret never authenticates
			(None, "s3cret-token", "s3cret-token"),  # unknown or disabled shortcode
		):
			with self.subTest(secret=secret, token=token), self.channel(name, secret, token):
				with self.assertRaises(frappe.PermissionError):
					collections.ingest_paybill(**callback())
		self.get_doc.assert_not_called()

	def test_token_in_the_body_is_not_accepted(self):
		with self.channel(token=""):
			with self.assertRaises(frappe.PermissionError):
				collections.ingest_paybill(**callback(token="s3cret-token"))

	def test_good_token_creates_one_unmatched_record_and_queues_matching(self):
		with self.channel():
			result = collections.ingest_paybill(cmd="x", token="s3cret-token", **callback())
		self.assertEqual(result, collections.PAYBILL_ACK)
		values = self.get_doc.call_args.args[0]
		self.assertEqual(
			(values["channel"], values["transaction_code"], values["amount"], values["sender"]),
			("EDK-PC-1", "UK12345678", 1250.0, "Jane Wanjiku"),
		)
		self.assertEqual(values["account_reference"], "ADM-1")
		self.assertNotIn("workflow_state", values)  # enters as New, never pre-matched
		raw = json.loads(values["raw_payload"])
		self.assertEqual(raw["TransID"], "UK12345678")
		self.assertTrue({"token", "cmd"}.isdisjoint(raw))
		self.enqueue.assert_called_once_with(
			"frappe_education_kenya.collections.match", queue="short", enqueue_after_commit=True, name="EC-1"
		)
		# Elevated only for the insert, then back to the caller.
		self.assertEqual([c.args[0] for c in self.set_user.call_args_list], ["Administrator", "Guest"])

	def test_replay_creates_no_second_record(self):
		self.db.exists.return_value = "EC-1"
		with self.channel():
			result = collections.ingest_paybill(**callback())
		self.assertEqual(result, collections.PAYBILL_ACK)
		self.get_doc.assert_not_called()
		self.enqueue.assert_not_called()

	def test_concurrent_replay_losing_the_insert_race_is_acknowledged(self):
		self.get_doc.return_value.insert.side_effect = frappe.UniqueValidationError
		with self.channel():
			result = collections.ingest_paybill(**callback())
		self.assertEqual(result, collections.PAYBILL_ACK)
		self.db.rollback.assert_called_once()
		self.enqueue.assert_not_called()

	def test_malformed_callbacks_are_rejected_without_a_record(self):
		for bad in (
			{"TransAmount": "0"},
			{"TransAmount": "10.123"},
			{"TransAmount": None},
			{"TransID": ""},
			{"TransTime": "not-a-time"},
		):
			with self.subTest(bad=bad), self.channel():
				result = collections.ingest_paybill(**callback(**bad))
				self.assertEqual(result, collections.PAYBILL_REJECT)
		self.get_doc.return_value.insert.assert_not_called()
		self.assertEqual(self.set_user.call_args_list[-1].args[0], "Guest")

	def test_blank_reference_lands_in_review_not_lost(self):
		with self.channel():
			collections.ingest_paybill(**callback(BillRefNumber=" "))
		self.assertEqual(self.get_doc.call_args.args[0]["account_reference"], "-")

	def test_validation_url_needs_the_token_and_accepts_everything_else(self):
		with self.channel():
			self.assertEqual(collections.validate_paybill(**callback()), collections.PAYBILL_ACK)
		with self.channel(token="wrong"), self.assertRaises(frappe.PermissionError):
			collections.validate_paybill(**callback())

	def test_transaction_time_is_east_africa_time_in_the_system_timezone(self):
		sent = (datetime.now(EAT) - timedelta(hours=1)).replace(microsecond=0)
		got = collections.paybill_time(sent.strftime("%Y%m%d%H%M%S"))
		self.assertEqual(got, sent.astimezone(ZoneInfo("UTC")).replace(tzinfo=None))

	def test_transaction_time_outside_the_window_is_refused(self):
		for delta in (-timedelta(days=8), timedelta(minutes=10)):
			with self.subTest(delta=delta), self.assertRaises(frappe.ValidationError):
				collections.paybill_time(trans_time(delta))

	def test_collection_payment_must_use_the_channel_mode_of_payment(self):
		doc = row(
			status="Approved",
			payment_entry=None,
			fees="F-1",
			sales_invoice=None,
			student="ADM-1",
			amount=100,
			channel="EDK-PC-1",
		)
		channel = row(bank_account="Bank - S", mode_of_payment="M-Pesa Paybill")
		docs = {"Electronic Collection": doc, "Payment Channel": channel}

		def entry(mode):
			return row(
				name="PE-1",
				party="ADM-1",
				paid_to="Bank - S",
				mode_of_payment=mode,
				paid_amount=100,
				received_amount=100,
				electronic_collection="EC-1",
				references=[row(reference_doctype="Fees", reference_name="F-1", allocated_amount=100)],
			)

		with (
			patch.object(frappe, "get_doc", side_effect=lambda doctype, *a, **k: docs[doctype]),
			patch.object(collections, "settings"),
			patch.object(collections, "invoice_for", return_value=row(customer="C-1")),
		):
			collections.validate_collection_payment(entry("M-Pesa Paybill"))
			with self.assertRaises(frappe.ValidationError):
				collections.validate_collection_payment(entry("Cash"))


class TestPaymentChannelRules(TestCase):
	def setUp(self):
		def fail(message, exc=frappe.ValidationError, **kwargs):
			raise exc(message)

		self.addCleanup(patch.stopall)
		patch.object(frappe, "throw", side_effect=fail).start()
		patch.object(payment_channel, "_", side_effect=lambda message: message).start()
		patch.object(frappe, "only_for").start()
		patch.object(
			frappe,
			"get_doc",
			return_value=row(company="School Co", is_group=0, disabled=0, account_type="Bank"),
		).start()
		self.mode_account = "Bank - S"
		self.mode_enabled = 1
		self.duplicate = None

		def get_value(doctype, *args, **kwargs):
			return self.mode_account if doctype == "Mode of Payment Account" else self.mode_enabled

		self.db = MagicMock(
			**{"get_single_value.return_value": "School Co", "get_value.side_effect": get_value}
		)
		self.db.exists.side_effect = lambda *a, **k: self.duplicate
		patch.object(frappe, "db", self.db).start()

	def validate(self, **values):
		channel = row(
			name="EDK-PC-1",
			provider="M-Pesa Paybill",
			shortcode="174379",
			bank_account="Bank - S",
			mode_of_payment="M-Pesa Paybill",
			enabled=1,
			**values,
		)
		payment_channel.PaymentChannel.validate(channel)

	def test_consistent_channel_is_accepted(self):
		self.validate()

	def test_mode_of_payment_must_post_to_the_channel_account(self):
		self.mode_account = "Cash - S"
		with self.assertRaises(frappe.ValidationError):
			self.validate()

	def test_disabled_mode_of_payment_is_refused(self):
		self.mode_enabled = 0
		with self.assertRaises(frappe.ValidationError):
			self.validate()

	def test_enabled_channels_need_distinct_provider_and_shortcode(self):
		self.duplicate = "EDK-PC-2"
		with self.assertRaises(frappe.ValidationError):
			self.validate()
