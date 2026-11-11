"""No-DB regression coverage; run with the bench Python unittest runner."""

from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe

from frappe_education_kenya import transport


def fare(trip_type="Two Way", amount=9000, effective_from="2026-01-01"):
	return frappe._dict(trip_type=trip_type, amount=amount, effective_from=effective_from)


class Subscription(frappe._dict):
	def get_doc_before_save(self):
		return self.get("_before")

	def precision(self, field):
		return 2


def subscription(**values):
	return Subscription(
		{
			"student": "STUDENT-1",
			"route": "ROUTE-1",
			"trip_type": "Two Way",
			"start_date": "2026-03-01",
			"discount_type": "None",
			"discount_value": 0,
			"discount_reason": "",
			"discount_approved_by": None,
			"sales_invoice": None,
			"subscription_status": "Active",
			**values,
		}
	)


class TestTransportFares(TestCase):
	def setUp(self):
		# Isolate framework message logging/translation, not pricing or permission decisions.
		def fail(message, exc=frappe.ValidationError, **kwargs):
			raise exc(message)

		self.addCleanup(patch.stopall)
		patch.object(frappe, "throw", side_effect=fail).start()
		patch.object(transport, "_", side_effect=lambda message: message).start()
		# flt(..., precision) needs a site for the rounding setting; the pricing rules under test do not.
		patch.object(
			transport, "flt", side_effect=lambda value, precision=None: round(float(value), precision or 2)
		).start()

	def test_invoice_role_denied_before_document_lookup(self):
		with (
			patch.object(frappe, "get_roles", return_value=["Transport Manager"]),
			# Not create=True: that skips the restore and deletes `local.session` for every later test.
			patch.object(frappe.local, "session", SimpleNamespace(user="transport@example.com")),
			patch.object(frappe, "get_doc") as load,
		):
			with self.assertRaises(frappe.PermissionError):
				transport.create_invoice("SUB-1")
		load.assert_not_called()

	def test_fare_lookup_rejects_filter_injection(self):
		with patch.object(frappe, "get_doc") as load:
			with self.assertRaises((frappe.ValidationError, TypeError)):
				transport.get_fare(["like", "%"], "Two Way", "2026-01-01")
		load.assert_not_called()

	def test_invoice_replay_preserves_existing_link(self):
		doc = subscription(sales_invoice="SINV-1")
		with (
			patch.object(frappe, "only_for"),
			patch.object(frappe, "has_permission"),
			patch.object(frappe, "db", MagicMock()),
			patch.object(frappe, "get_doc", return_value=doc) as load,
		):
			result = transport.create_invoice("SUB-1")
		self.assertEqual(result["name"], "SINV-1")
		load.assert_called_once_with("Transport Subscription", "SUB-1")

	def test_fare_by_trip_type(self):
		fares = [
			fare(amount=9000),
			fare("One Way Morning", 5000),
			fare("One Way Evening", 5500),
			fare(amount=9500, effective_from="2026-04-01"),
		]
		self.assertEqual(transport.select_fare(fares, "One Way Morning", "2026-03-01"), 5000)
		self.assertEqual(transport.select_fare(fares, "One Way Evening", "2026-03-01"), 5500)
		self.assertEqual(transport.select_fare(fares, "Two Way", "2026-03-31"), 9000)
		self.assertEqual(transport.select_fare(fares, "Two Way", "2026-04-01"), 9500)
		with self.assertRaises(frappe.ValidationError):
			transport.select_fare(fares, "Two Way", "2025-12-31")

	def test_duplicate_effective_date_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			transport.validate_fares([fare(), fare(amount=10000)])
		transport.validate_fares([fare(), fare("One Way Morning")])

	def test_discount_cap(self):
		self.assertEqual(transport.net_fare(9000, "Percent", 10, "Sibling"), Decimal(8100))
		self.assertEqual(transport.net_fare(9000, "Amount", 9000, "Waived"), 0)
		for kind, value, reason in [
			("Percent", 101, "Reason"),
			("Amount", 9001, "Reason"),
			("Percent", -1, "Reason"),
			("None", 1, "Reason"),
			("Amount", 1, "  "),
		]:
			with self.subTest(kind=kind, value=value), self.assertRaises(frappe.ValidationError):
				transport.net_fare(9000, kind, value, reason)

	def test_finite_nonnegative_controls(self):
		for value in ("NaN", "Infinity", "-Infinity", -1, "1e10000", {}, True):
			with self.subTest(value=value), self.assertRaises(frappe.ValidationError):
				transport.net_fare(value)
			with self.subTest(discount=value), self.assertRaises(frappe.ValidationError):
				transport.net_fare(9000, "Amount", value, "Reason")

	def test_unauthorized_discount_insert_and_update(self):
		with patch.object(frappe, "get_roles", return_value=["Transport Manager"]):
			for values in ({"discount_value": 1, "discount_type": "Amount"}, {"discount_reason": "Changed"}):
				with self.subTest(values=values), self.assertRaises(frappe.PermissionError):
					transport.validate_subscription(subscription(**values))
			old = subscription(discount_type="Amount", discount_value=100, discount_reason="Approved")
			doc = subscription(**dict(old), _before=old)
			doc.discount_value = 101
			with self.assertRaises(frappe.PermissionError):
				transport.validate_subscription(doc)

	def test_approval_spoof_and_invoice_link_spoof_rejected(self):
		for values in ({"discount_approved_by": "bursar@example.com"}, {"sales_invoice": "SINV-1"}):
			with self.subTest(values=values), self.assertRaises(frappe.PermissionError):
				transport.validate_subscription(subscription(**values))

	def test_start_date_lookup_and_server_approval(self):
		doc = subscription(discount_type="Percent", discount_value=10, discount_reason="Sibling")
		with (
			patch.object(frappe, "get_roles", return_value=["Bursar"]),
			patch.object(frappe, "session", SimpleNamespace(user="bursar@example.com")),
			patch.object(
				frappe,
				"get_doc",
				return_value=SimpleNamespace(fares=[fare(), fare(amount=12000, effective_from="2026-04-01")]),
			),
		):
			transport.validate_subscription(doc)
			self.assertEqual((doc.fee_amount, doc.net_amount), (9000, 8100))
			self.assertEqual(doc.discount_approved_by, "bursar@example.com")

	def test_unchanged_approved_discount_allowed_to_transport_manager(self):
		old = subscription(
			discount_type="Amount",
			discount_value=100,
			discount_reason="Approved",
			discount_approved_by="bursar@example.com",
		)
		doc = subscription(**dict(old), _before=old)
		with (
			patch.object(frappe, "get_roles", return_value=["Transport Manager"]),
			patch.object(frappe, "get_doc", return_value=SimpleNamespace(fares=[fare()])),
		):
			transport.validate_subscription(doc)
		self.assertEqual(doc.net_amount, 8900)
		self.assertEqual(doc.discount_approved_by, "bursar@example.com")

	def test_invoiced_selection_is_immutable(self):
		old = subscription(sales_invoice="SINV-1", fee_amount=9000, net_amount=9000)
		doc = subscription(**dict(old), _before=old)
		doc.start_date = "2026-04-01"
		with self.assertRaises(frappe.ValidationError):
			transport.validate_subscription(doc)

	def test_term_fee_patch_idempotent(self):
		route = MagicMock()
		route.fares = []
		route.append.side_effect = lambda field, values: route.fares.append(frappe._dict(values))
		query = MagicMock()
		query.from_.return_value.select.return_value.for_update.return_value.run.return_value = [
			frappe._dict(name="ROUTE-1", term_fee=9750)
		]
		with (
			patch.object(frappe, "qb", query),
			patch.object(frappe, "db", MagicMock()),
			patch.object(frappe, "get_doc", return_value=route),
			patch.object(frappe, "clear_cache"),
		):
			transport.convert_transport_term_fee_to_fares()
			preserved = deepcopy(route.fares)
			transport.convert_transport_term_fee_to_fares()
		self.assertEqual(route.fares, preserved)
		self.assertEqual(len(route.fares), 1)
		self.assertEqual(route.fares[0].amount, 9750)
		self.assertEqual(route.fares[0].trip_type, "Two Way")
		self.assertEqual(transport.select_fare(route.fares, "Two Way", "2026-01-01"), 9750)
		route.save.assert_called_once()

	def test_invoice_uses_selected_net_fare_and_never_submits(self):
		doc = subscription(net_amount=8100)
		doc.save = MagicMock()
		doc.db_set = MagicMock()
		invoice = MagicMock(name="invoice")
		invoice.name = "SINV-1"
		settings = frappe._dict(
			company="School",
			cost_center="School CC",
			transport_item="Transport",
			default_transport_account="Transport Income",
			default_currency="KES",
		)
		account = frappe._dict(company="School", is_group=0, disabled=0, root_type="Income")
		cost_center = frappe._dict(company="School", is_group=0)
		item = frappe._dict(disabled=0, is_stock_item=0, is_sales_item=1)
		payloads = []

		def get_doc(doctype, *args):
			if isinstance(doctype, dict):
				payloads.append(doctype)
				return invoice
			return {
				"Transport Subscription": doc,
				"Account": account,
				"Cost Center": cost_center,
				"Item": item,
			}[doctype]

		def get_value(doctype, *args, **kwargs):
			return {"Company": "KES", "Student": "CUSTOMER-1", "Transport Subscription": "SUB-1"}[doctype]

		with (
			patch.object(frappe, "only_for") as role_gate,
			patch.object(frappe, "has_permission") as permission_gate,
			patch.object(frappe, "get_doc", side_effect=get_doc),
			patch.object(frappe, "get_single", return_value=settings),
			patch.object(frappe, "db", MagicMock(get_value=get_value)),
			patch.object(transport, "today", return_value="2026-01-01"),
		):
			result = transport.create_invoice("SUB-1")
		role_gate.assert_called_once_with("Bursar")
		self.assertTrue(permission_gate.called)
		self.assertTrue(result["ok"])
		self.assertEqual(payloads[0]["customer"], "CUSTOMER-1")
		self.assertEqual(payloads[0]["items"][0]["rate"], 8100)
		invoice.insert.assert_called_once_with()
		invoice.submit.assert_not_called()
		doc.db_set.assert_called_once_with("sales_invoice", "SINV-1")
