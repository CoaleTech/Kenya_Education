"""Effective-dated transport pricing and explicit draft invoicing."""

from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

TRIP_TYPES = ("One Way Morning", "One Way Evening", "Two Way")
DISCOUNT_FIELDS = ("discount_type", "discount_value", "discount_reason")
LEGACY_EFFECTIVE_FROM = "1000-01-01"


def nonnegative_amount(value, label):
	try:
		amount = Decimal(str(value if value not in (None, "") else 0))
	except (InvalidOperation, ValueError):
		frappe.throw(_("{0} must be a finite non-negative amount.").format(label))
	if not amount.is_finite() or not 0 <= amount <= Decimal("999999999999"):
		frappe.throw(_("{0} must be finite and between 0 and 999999999999.").format(label))
	return amount


def validate_fares(fares):
	seen = set()
	for fare in fares:
		if fare.get("trip_type") not in TRIP_TYPES or not fare.get("effective_from"):
			frappe.throw(_("Each fare needs a valid trip type and effective date."))
		key = (fare.get("trip_type"), getdate(fare.get("effective_from")))
		if key in seen:
			frappe.throw(_("Only one fare per trip type and effective date is allowed."))
		seen.add(key)
		nonnegative_amount(fare.get("amount"), _("Fare"))


def select_fare(fares, trip_type, start_date):
	if trip_type not in TRIP_TYPES or not start_date:
		frappe.throw(_("Select a trip type and start date."))
	validate_fares(fares)
	eligible = [
		fare
		for fare in fares
		if fare.get("trip_type") == trip_type and getdate(fare.get("effective_from")) <= getdate(start_date)
	]
	if not eligible:
		frappe.throw(_("No fare is effective for this trip type on the subscription start date."))
	latest = max(eligible, key=lambda fare: getdate(fare.get("effective_from")))
	return nonnegative_amount(latest.get("amount"), _("Fare"))


def net_fare(fare, discount_type="None", discount_value=0, discount_reason=None):
	fare = nonnegative_amount(fare, _("Fare"))
	value = nonnegative_amount(discount_value, _("Discount"))
	if discount_type not in ("None", "Percent", "Amount"):
		frappe.throw(_("Invalid discount type."))
	if discount_type == "None" and value:
		frappe.throw(_("Select a discount type before entering a discount."))
	if discount_type == "Percent" and value > 100:
		frappe.throw(_("Discount cannot exceed 100 percent."))
	discount = fare * value / 100 if discount_type == "Percent" else value
	if discount > fare:
		frappe.throw(_("Discount cannot exceed the fare."))
	if value and not (discount_reason or "").strip():
		frappe.throw(_("A reason is required for a discount."))
	return fare - discount


def validate_subscription(doc):
	old = doc.get_doc_before_save()
	defaults = {"discount_type": "None", "discount_value": 0, "discount_reason": ""}
	changed = any(
		(doc.get(field) or defaults[field]) != ((old.get(field) if old else None) or defaults[field])
		for field in DISCOUNT_FIELDS
	)
	previous_approver = old.get("discount_approved_by") if old else None
	if (doc.get("discount_approved_by") or "") != (previous_approver or ""):
		frappe.throw(_("Discount approval is set by the server."), frappe.PermissionError)
	if changed and not {"Bursar", "Head Teacher"}.intersection(frappe.get_roles()):
		frappe.throw(_("Only a Bursar or Head Teacher may change discount fields."), frappe.PermissionError)
	if old and (doc.get("sales_invoice") or "") != (old.get("sales_invoice") or ""):
		frappe.throw(_("Invoice linkage is set by the invoice action."), frappe.PermissionError)
	if not old and doc.get("sales_invoice"):
		frappe.throw(_("Invoice linkage is set by the invoice action."), frappe.PermissionError)
	if (
		old
		and old.get("sales_invoice")
		and any(
			doc.get(field) != old.get(field)
			for field in ("student", "route", "trip_type", "start_date", *DISCOUNT_FIELDS)
		)
	):
		frappe.throw(_("An invoiced subscription cannot change its student, fare selection or discount."))
	if doc.get("end_date") and getdate(doc.end_date) < getdate(doc.start_date):
		frappe.throw(_("End date cannot be before start date."))
	route = frappe.get_doc("Transport Route", doc.route)
	fare = select_fare(route.fares, doc.trip_type, doc.start_date)
	doc.fee_amount = flt(fare, doc.precision("fee_amount"))
	doc.net_amount = flt(
		net_fare(doc.fee_amount, doc.discount_type or "None", doc.discount_value, doc.discount_reason),
		doc.precision("net_amount"),
	)
	if (
		old
		and old.get("sales_invoice")
		and (
			Decimal(str(old.fee_amount)) != Decimal(str(doc.fee_amount))
			or Decimal(str(old.net_amount)) != Decimal(str(doc.net_amount))
		)
	):
		frappe.throw(
			_("The fare of an invoiced subscription cannot change. Keep its effective fare history.")
		)
	if changed:
		doc.discount_approved_by = frappe.session.user if doc.discount_value else None


@frappe.whitelist(methods=["GET"])
def get_fare(route: str, trip_type: str, start_date: str) -> dict:
	for value in (route, trip_type, start_date):
		if not isinstance(value, str) or not value:
			frappe.throw(_("Route, trip type and start date are required."))
	frappe.has_permission("Transport Route", "read", doc=route, throw=True)
	return {
		"fee_amount": float(
			select_fare(frappe.get_doc("Transport Route", route).fares, trip_type, start_date)
		)
	}


@frappe.whitelist(methods=["GET"])
def route_summary(route: str) -> dict:
	if not isinstance(route, str) or not route:
		frappe.throw(_("Route is required."))
	frappe.has_permission("Transport Route", "read", doc=route, throw=True)
	frappe.has_permission("Transport Subscription", "read", throw=True)
	from frappe.query_builder.functions import Count, Sum

	subscription = frappe.qb.DocType("Transport Subscription")
	rows = (
		frappe.qb.from_(subscription)
		.select(Count(subscription.name).as_("subscribers"), Sum(subscription.net_amount).as_("term_revenue"))
		.where((subscription.route == route) & (subscription.subscription_status == "Active"))
	).run(as_dict=True)
	return {
		"total_subscribers": rows[0].subscribers,
		"monthly_revenue": flt(rows[0].term_revenue) / 3,
	}


@frappe.whitelist(methods=["POST"])
def create_invoice(subscription: str) -> dict:
	if not isinstance(subscription, str) or not subscription:
		frappe.throw(_("Subscription is required."))
	frappe.only_for("Bursar")
	frappe.has_permission("Transport Subscription", "write", doc=subscription, throw=True)
	frappe.has_permission("Sales Invoice", "create", throw=True)
	frappe.db.get_value("Transport Subscription", subscription, "name", for_update=True)
	doc = frappe.get_doc("Transport Subscription", subscription)
	if doc.sales_invoice:
		frappe.has_permission("Sales Invoice", "read", doc=doc.sales_invoice, throw=True)
		return {"ok": True, "name": doc.sales_invoice, "message": _("Invoice already linked.")}
	# Re-run server pricing and discount guards before using any stored amount.
	doc.save()
	settings = frappe.get_single("Education Kenya Settings")
	for field in (
		"company",
		"cost_center",
		"transport_item",
		"default_transport_account",
		"default_currency",
	):
		if not settings.get(field):
			frappe.throw(_("Configure {0} in Education Kenya Settings before invoicing.").format(field))
	company = settings.company
	account = frappe.get_doc("Account", settings.default_transport_account)
	cost_center = frappe.get_doc("Cost Center", settings.cost_center)
	item = frappe.get_doc("Item", settings.transport_item)
	if account.company != company or account.is_group or account.disabled or account.root_type != "Income":
		frappe.throw(
			_("Transport income account must be an enabled ledger account in the configured company.")
		)
	if cost_center.company != company or cost_center.is_group:
		frappe.throw(_("Transport cost center must belong to the configured company and cannot be a group."))
	if item.disabled or item.is_stock_item or not item.is_sales_item:
		frappe.throw(_("Transport item must be an enabled non-stock sales item."))
	if frappe.db.get_value("Company", company, "default_currency") != settings.default_currency:
		frappe.throw(_("Transport currency must match the configured company's currency."))
	frappe.has_permission("Student", "read", doc=doc.student, throw=True)
	customer = frappe.db.get_value("Student", doc.student, "customer")
	if not customer:
		frappe.throw(_("The student must have a linked Customer before invoicing."))
	if doc.subscription_status != "Active" or not doc.net_amount:
		frappe.throw(_("Only an active subscription with a positive net fare can be invoiced."))
	invoice = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": customer,
			"company": company,
			"posting_date": today(),
			"due_date": today(),
			"currency": settings.default_currency,
			"cost_center": settings.cost_center,
			"ignore_pricing_rule": 1,
			"items": [
				{
					"item_code": settings.transport_item,
					"qty": 1,
					"rate": doc.net_amount,
					"income_account": settings.default_transport_account,
					"cost_center": settings.cost_center,
				}
			],
		}
	)
	invoice.insert()
	# Explicit Bursar action owns this read-only linkage; no permission bypass or submission.
	doc.db_set("sales_invoice", invoice.name)
	return {"ok": True, "name": invoice.name, "message": _("Draft transport invoice created.")}


def convert_transport_term_fee_to_fares():
	"""Post-model-sync: preserve the retained legacy SQL column before it is retired.

	Frappe schema sync keeps removed columns. Query Builder deliberately reads that
	column, not the new route meta. The baseline covers all supported MariaDB dates.
	Never drop the column here: it remains a recovery source, not an application field.
	"""
	if not frappe.db.has_column("Transport Route", "term_fee"):
		return
	route_table = frappe.qb.DocType("Transport Route")
	rows = (frappe.qb.from_(route_table).select(route_table.name, route_table.term_fee).for_update()).run(
		as_dict=True
	)
	for row in rows:
		amount = nonnegative_amount(row.term_fee, _("Legacy term fee"))
		route = frappe.get_doc("Transport Route", row.name)
		baseline = [
			fare
			for fare in route.fares
			if fare.trip_type == "Two Way" and str(fare.effective_from) == LEGACY_EFFECTIVE_FROM
		]
		if baseline:
			if len(baseline) != 1 or nonnegative_amount(baseline[0].amount, _("Fare")) != amount:
				frappe.throw(_("Legacy fare conflicts with the baseline for route {0}.").format(row.name))
			continue
		route.append(
			"fares",
			{"trip_type": "Two Way", "amount": float(amount), "effective_from": LEGACY_EFFECTIVE_FROM},
		)
		route.save()
	subscription = frappe.qb.DocType("Transport Subscription")
	frappe.qb.update(subscription).set(subscription.trip_type, "Two Way").where(
		subscription.trip_type.isnull() | (subscription.trip_type == "")
	).run()
	frappe.qb.update(subscription).set(subscription.net_amount, subscription.fee_amount).where(
		(subscription.net_amount.isnull() | (subscription.net_amount == 0))
		& (subscription.discount_value.isnull() | (subscription.discount_value == 0))
	).run()
	# Remove only obsolete fetch customizations; model sync clears the standard DocField.
	frappe.db.delete(
		"Property Setter",
		{
			"doc_type": "Transport Subscription",
			"field_name": "fee_amount",
			"property": "fetch_from",
			"value": "route.term_fee",
		},
	)
	frappe.clear_cache(doctype="Transport Subscription")
