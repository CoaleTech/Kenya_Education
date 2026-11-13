"""Bursary reservations and pledge rollups; accounting stays in ERPNext."""

from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, now_datetime, nowdate

from frappe_education_kenya.parent_ops import guardian_students


def money(value):
	try:
		amount = Decimal(str(value))
	except (InvalidOperation, ValueError, TypeError):
		frappe.throw(_("Enter a valid amount"))
	if not amount.is_finite() or amount <= 0 or amount != amount.quantize(Decimal("0.01")):
		frappe.throw(_("Amount must be positive with at most two decimal places"))
	return amount


def gate(doctype, name, role="Bursar"):
	frappe.only_for([role])
	frappe.has_permission(doctype, "write", doc=name, throw=True)


def settings():
	doc = frappe.get_single("Education Kenya Settings")
	if not all(
		doc.get(f)
		for f in (
			"company",
			"default_currency",
			"default_payment_account",
			"default_payment_mode",
			"cost_center",
		)
	):
		frappe.throw(
			_(
				"Configure company, currency, payment account, payment mode and cost center in Education Kenya Settings"
			)
		)
	if frappe.db.get_value("Company", doc.company, "default_currency") != doc.default_currency:
		frappe.throw(_("School currency must match the configured company's currency"))
	if frappe.db.get_value("Cost Center", doc.cost_center, "company") != doc.company:
		frappe.throw(_("Cost center belongs to another company"))
	return doc


def invoice_for(student, reference, config, reference_doctype="Sales Invoice"):
	if reference_doctype not in ("Sales Invoice", "Fees") or not reference:
		frappe.throw(_("Select a submitted Fees or Sales Invoice target"))
	invoice = frappe.get_doc(reference_doctype, reference, for_update=True)
	invoice.check_permission("read")
	if reference_doctype == "Sales Invoice":
		customer = frappe.db.get_value("Student", student, "customer")
		if not customer or invoice.customer != customer:
			frappe.throw(_("Invoice does not belong to this student's Customer"))
	elif invoice.student != student:
		frappe.throw(_("Fees belongs to another student"))
	if invoice.company != config.company or invoice.currency != config.default_currency:
		frappe.throw(_("Target company or currency differs from school settings"))
	if invoice.docstatus != 1 or invoice.get("is_return") or invoice.outstanding_amount <= 0:
		frappe.throw(_("Select a submitted target with an outstanding balance"))
	return invoice


def make_payment(
	student, reference, amount, bank_account=None, reference_doctype="Sales Invoice", mode_of_payment=None
):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	config = settings()
	invoice = invoice_for(student, reference, config, reference_doctype)
	amount = money(amount)
	if amount > Decimal(str(invoice.outstanding_amount)):
		frappe.throw(_("Amount exceeds the outstanding balance"))
	account = frappe.get_doc("Account", bank_account or config.default_payment_account)
	if (
		account.company != config.company
		or account.is_group
		or account.disabled
		or account.account_type not in ("Bank", "Cash")
	):
		frappe.throw(_("Select an enabled bank/cash account in the configured company"))
	if (account.account_currency or config.default_currency) != config.default_currency:
		frappe.throw(_("Payment account currency differs from school currency"))
	receivable = invoice.get("debit_to") or invoice.get("receivable_account")
	receivable_doc = frappe.get_doc("Account", receivable)
	if receivable_doc.company != config.company or receivable_doc.account_currency != config.default_currency:
		frappe.throw(_("Receivable account company or currency differs from school settings"))
	if reference_doctype == "Sales Invoice":
		pe = get_payment_entry("Sales Invoice", invoice.name, bank_account=account.name)
		if pe.deductions or len(pe.references) != 1 or pe.references[0].get("payment_term"):
			frappe.throw(
				_(
					"Use the standard Payment Entry form for invoices with discounts or payment-term allocations"
				)
			)
	else:
		# Native Student/Fees ledger, not Student.customer: Fees.make_gl_entries.
		# ERPNext's convenience helper assumes company_currency (3577), which
		# legacy Fees does not define. The standard controller supports Student.
		if frappe.db.get_value("Party Type", "Student", "account_type") != "Receivable":
			frappe.throw(_("Education Student receivable Party Type must be configured"))
		pe = frappe.new_doc("Payment Entry")
		pe.update(
			{
				"payment_type": "Receive",
				"company": config.company,
				"party_type": "Student",
				"party": student,
				"paid_from": receivable,
				"paid_to": account.name,
				"paid_from_account_currency": config.default_currency,
				"paid_to_account_currency": config.default_currency,
				"posting_date": nowdate(),
			}
		)
		pe.append(
			"references",
			{
				"reference_doctype": "Fees",
				"reference_name": invoice.name,
				"total_amount": invoice.grand_total,
				"outstanding_amount": invoice.outstanding_amount,
			},
		)
	pe.paid_amount = pe.received_amount = float(amount)
	pe.references[0].allocated_amount = float(amount)
	pe.mode_of_payment = mode_of_payment or config.default_payment_mode
	pe.cost_center = config.cost_center
	pe.reference_no = invoice.name
	pe.reference_date = nowdate()
	pe.setup_party_account_field()
	pe.set_missing_values()
	pe.set_exchange_rate()
	pe.set_amounts()
	return pe


def allocation_total(rows):
	return sum(
		(
			Decimal(str(row.amount))
			for row in rows
			if row.payment_entry and frappe.db.get_value("Payment Entry", row.payment_entry, "docstatus") != 2
		),
		Decimal(0),
	)


@frappe.whitelist(methods=["POST"])
def allocate(award: str, fees: str, amount: float, reference_doctype: str = "Sales Invoice"):
	gate("Bursary Award", award)
	doc = frappe.get_doc("Bursary Award", award, for_update=True)
	if doc.workflow_state not in ("Approved", "Allocated"):
		frappe.throw(_("Only approved awards can be allocated"))
	if not getdate(doc.valid_from) <= getdate(nowdate()) <= getdate(doc.valid_to):
		frappe.throw(_("Award is outside its validity dates"))
	amount = money(amount)
	# One live reservation per award/target makes retries idempotent.
	for row in doc.allocations:
		if (
			row.reference_doctype == reference_doctype
			and row.reference_name == fees
			and frappe.db.get_value("Payment Entry", row.payment_entry, "docstatus") != 2
		):
			if Decimal(str(row.amount)) != amount:
				frappe.throw(_("A different allocation already exists for this invoice"))
			return {"ok": True, "name": row.payment_entry, "message": _("Existing draft allocation")}
	if allocation_total(doc.allocations) + amount > Decimal(str(doc.amount)):
		frappe.throw(_("Allocation exceeds the award amount"))
	pe = make_payment(doc.student, fees, amount, reference_doctype=reference_doctype)
	pe.bursary_award = doc.name
	pe.fee_pledge = doc.pledge
	pe.flags.finance_action = True
	pe.insert()
	doc.append(
		"allocations",
		{
			"reference_doctype": reference_doctype,
			"reference_name": fees,
			"amount": float(amount),
			"payment_entry": pe.name,
			"allocated_on": now_datetime(),
		},
	)
	doc.flags.finance_action = True
	doc.workflow_state = "Allocated"
	doc.save()
	if doc.pledge:
		refresh_pledge(doc.pledge)
	return {
		"ok": True,
		"name": pe.name,
		"message": _("Draft Payment Entry created; Bursar submission is required"),
	}


def pledge_total(name):
	from frappe.query_builder.functions import Sum

	pe = frappe.qb.DocType("Payment Entry")
	paid = (
		frappe.qb.from_(pe)
		.select(Sum(pe.paid_amount))
		.where((pe.fee_pledge == name) & (pe.docstatus == 1))
		.run()[0][0]
		or 0
	)
	allocation = frappe.qb.DocType("Bursary Allocation")
	award = frappe.qb.DocType("Bursary Award")
	# Draft reservations count once; their submitted Payment Entries are above.
	reserved = (
		frappe.qb.from_(allocation)
		.join(award)
		.on(allocation.parent == award.name)
		.join(pe)
		.on(allocation.payment_entry == pe.name)
		.select(Sum(allocation.amount))
		.where((award.pledge == name) & (award.workflow_state == "Allocated") & (pe.docstatus == 0))
		.run()[0][0]
		or 0
	)
	return Decimal(str(paid)) + Decimal(str(reserved))


def refresh_pledge(name):
	doc = frappe.get_doc("Fee Pledge", name, for_update=True)
	doc.flags.finance_action = True
	doc.save()


def validate_payment(doc, method=None):
	old = doc.get_doc_before_save()
	linked = any(doc.get(f) for f in ("bursary_award", "electronic_collection", "fee_pledge"))
	if old and any(old.get(f) != doc.get(f) for f in ("bursary_award", "electronic_collection")):
		frappe.throw(_("Finance source links cannot be changed"))
	if not linked:
		return
	if (doc.bursary_award or doc.electronic_collection) and doc.is_new() and not doc.flags.finance_action:
		frappe.throw(_("Create linked payments through the finance action"))
	config = settings()
	if (
		doc.company != config.company
		or doc.payment_type != "Receive"
		or doc.party_type not in ("Customer", "Student")
	):
		frappe.throw(_("Invalid company or party for school finance payment"))
	if (
		doc.paid_from_account_currency != config.default_currency
		or doc.paid_to_account_currency != config.default_currency
	):
		frappe.throw(_("School finance payments must use school currency"))
	if doc.fee_pledge:
		pledge = frappe.get_doc("Fee Pledge", doc.fee_pledge, for_update=True)
		if (
			pledge.student
			if doc.party_type == "Student"
			else frappe.db.get_value("Student", pledge.student, "customer")
		) != doc.party:
			frappe.throw(_("Payment party differs from the pledge student"))
	if doc.bursary_award:
		award = frappe.get_doc("Bursary Award", doc.bursary_award, for_update=True)
		if doc.fee_pledge != award.pledge:
			frappe.throw(_("Payment pledge differs from its award"))
		if not doc.is_new():
			rows = [r for r in award.allocations if r.payment_entry == doc.name]
			if len(rows) != 1 or Decimal(str(rows[0].amount)) != Decimal(str(doc.paid_amount)):
				frappe.throw(_("Payment amount differs from the award reservation"))
			if (
				len(doc.references) != 1
				or doc.references[0].reference_name != rows[0].reference_name
				or doc.references[0].reference_doctype != rows[0].reference_doctype
				or Decimal(str(doc.references[0].allocated_amount)) != Decimal(str(rows[0].amount))
			):
				frappe.throw(_("Payment references differ from the award reservation"))
			invoice_for(award.student, rows[0].reference_name, config, rows[0].reference_doctype)
		if (
			award.student
			if doc.party_type == "Student"
			else frappe.db.get_value("Student", award.student, "customer")
		) != doc.party:
			frappe.throw(_("Payment party differs from its award student"))
	if doc.electronic_collection:
		from frappe_education_kenya.collections import validate_collection_payment

		validate_collection_payment(doc)


def before_payment_submit(doc, method=None):
	if any(doc.get(f) for f in ("bursary_award", "electronic_collection", "fee_pledge")):
		frappe.only_for(["Bursar"])
		validate_payment(doc)


def payment_rollup(doc, method=None):
	if doc.get("bursary_award"):
		award = frappe.get_doc("Bursary Award", doc.bursary_award, for_update=True)
		award.db_set("allocated_amount", float(allocation_total(award.allocations)))
	if doc.get("fee_pledge"):
		refresh_pledge(doc.fee_pledge)
	if method == "on_cancel" and doc.get("electronic_collection"):
		frappe.throw(
			_("Posted collection payments cannot be cancelled; use an authorised accounting reversal")
		)


def daily_reminders():
	from frappe.core.doctype.sms_settings.sms_settings import send_sms

	from frappe_education_kenya.parent_ops import has_messaging_consent

	# Default 0 settings are explicit kill switches; absent consent still logs a reason.
	config = frappe.get_single("Education Settings")
	for name in frappe.get_all(
		"Fee Pledge", filters={"status": ["in", ["Open", "Partly Met"]]}, pluck="name"
	):
		doc = frappe.get_doc("Fee Pledge", name, for_update=True)
		if getdate(nowdate()) < getdate(add_days(doc.due_date, -cint(doc.reminder_days_before))):
			continue
		if any(getdate(row.sent_on) == getdate(nowdate()) for row in doc.reminders):
			continue
		result = _("Disabled")
		if not has_messaging_consent(doc.guardian, doc.student):
			result = _("No active consent")
		elif config.get("kenya_enable_pledge_reminders") and config.get("kenya_enable_scheduled_messages"):
			mobile = frappe.db.get_value("Guardian", doc.guardian, "mobile_number")
			if not mobile or not frappe.db.get_single_value("SMS Settings", "sms_gateway_url"):
				result = _("Missing guardian mobile or SMS gateway")
			else:
				try:
					# Recheck immediately before dispatch: absent/revoked consent never sends.
					if has_messaging_consent(doc.guardian, doc.student):
						send_sms(
							[mobile],
							_("Fee pledge {0} is due on {1}. Please contact the school bursar.").format(
								doc.name, doc.due_date
							),
							success_msg=False,
						)
						result = _("Dispatched; gateway delivery unconfirmed")
					else:
						result = _("No active consent")
				except Exception:
					frappe.log_error(
						title=_("Fee pledge reminder failed"),
						reference_doctype="Fee Pledge",
						reference_name=doc.name,
					)
					result = _("Dispatch failed; contact the System Manager")
		doc.append("reminders", {"sent_on": now_datetime(), "channel": "SMS", "result": result})
		doc.flags.finance_action = True
		doc.save()


FINANCE_VIEW_ROLES = {"System Manager", "Bursar", "Head Teacher", "Accounts Manager", "Accounts User"}


def guardian_finance_query(user=None, doctype=None):
	user = user or frappe.session.user
	if user == "Administrator" or FINANCE_VIEW_ROLES.intersection(frappe.get_roles(user)):
		return ""
	students = guardian_students(user)
	if not students:
		return "1=0"
	return "`tab{0}`.`student` in ({1})".format(doctype, ", ".join(frappe.db.escape(s) for s in students))


def fee_pledge_query(user=None):
	return guardian_finance_query(user, "Fee Pledge")


def bursary_award_query(user=None):
	return guardian_finance_query(user, "Bursary Award")


def guardian_finance_permission(doc, ptype=None, user=None, debug=False):
	user = user or frappe.session.user
	if user == "Administrator" or FINANCE_VIEW_ROLES.intersection(frappe.get_roles(user)):
		return None
	if ptype not in ("read", "select", "print"):
		return False
	return doc.student in guardian_students(user)


def setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(
		{
			"Payment Entry": [
				{
					"fieldname": field,
					"label": label,
					"fieldtype": "Link",
					"options": label,
					"insert_after": "reference_date",
					"read_only": int(field != "fee_pledge"),
					"allow_on_submit": 0,
				}
				for field, label in (
					("fee_pledge", "Fee Pledge"),
					("bursary_award", "Bursary Award"),
					("electronic_collection", "Electronic Collection"),
				)
			]
		}
	)
	load_workflow("bursary_award")


def load_workflow(filename):
	import json
	from pathlib import Path

	data = json.loads((Path(__file__).parent / "finance_workflows" / (filename + ".json")).read_text())
	for row in data["states"]:
		if not frappe.db.exists("Workflow State", row["state"]):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": row["state"]}).insert()
	for row in data["transitions"]:
		if not frappe.db.exists("Workflow Action Master", row["action"]):
			frappe.get_doc(
				{"doctype": "Workflow Action Master", "workflow_action_name": row["action"]}
			).insert()
	if frappe.db.exists("Workflow", data["name"]):
		doc = frappe.get_doc("Workflow", data["name"])
		doc.update(data)
		doc.save()
	else:
		frappe.get_doc(data).insert()
