"""Electronic-collection inbox: M-Pesa Paybill ingress, matching and Bursar-approved posting.

KCB and Co-operative Bank ingress still await provider payload samples.
"""

import hmac
import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import get_system_timezone, now_datetime
from frappe.utils.password import get_decrypted_password

from frappe_education_kenya.bursary import gate, invoice_for, load_workflow, make_payment, money, settings

# Safaricom Daraja C2B callback, same contract coale_payments consumes (api/m_pesa_api.py `confirmation`):
# JSON POST of TransactionType, TransID, TransTime (YYYYMMDDHHMMSS, East Africa Time), TransAmount,
# BusinessShortCode, BillRefNumber, InvoiceNumber, OrgAccountBalance, ThirdPartyTransID, MSISDN,
# FirstName, MiddleName, LastName. Daraja cannot sign or add headers, so the channel secret rides on the
# registered URL as `?token=`. Register both URLs with Safaricom:
#   /api/method/frappe_education_kenya.collections.ingest_paybill?token=<Ingress Token>   (confirmation)
#   /api/method/frappe_education_kenya.collections.validate_paybill?token=<Ingress Token> (validation)
# The URLs avoid "mpesa" and "exec"-like words that Daraja rejects in registered URLs.
PAYBILL_ACK = {"ResultCode": 0, "ResultDesc": "Accepted"}
PAYBILL_REJECT = {"ResultCode": 1, "ResultDesc": "Rejected"}
EAT = ZoneInfo("Africa/Nairobi")
# Outside this window a callback is forged or stale; replays inside it are absorbed by transaction_code.
MAX_AGE = timedelta(days=7)
MAX_SKEW = timedelta(minutes=5)


def paybill_log():
	log = frappe.logger("education_kenya_paybill", allow_site=True, file_count=10)
	# Frappe's default level (ERROR outside a dev server) would silently drop refusals and replays.
	log.setLevel(logging.INFO)
	return log


def paybill_channel(shortcode):
	"""Return the enabled Paybill channel for this shortcode, only if the URL token matches its secret.

	Daraja posts JSON, and Frappe then builds `form_dict` from the body alone, dropping the query string,
	so the token has to be read from the request's own query args.
	"""
	token = (frappe.request.args.get("token") if frappe.request else "") or ""
	name = frappe.db.get_value(
		"Payment Channel", {"provider": "M-Pesa Paybill", "shortcode": shortcode, "enabled": 1}
	)
	secret = name and get_decrypted_password("Payment Channel", name, "ingress_token", raise_exception=False)
	# An unset secret never authenticates; compare_digest keeps the comparison constant-time.
	if not secret or not hmac.compare_digest(secret.encode(), token.encode()):
		paybill_log().warning("Paybill callback refused: shortcode=%s", shortcode)
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return name


def paybill_time(value):
	"""Daraja TransTime (EAT) as a naive system-timezone datetime inside the accepted window."""
	try:
		sent = datetime.strptime(str(value), "%Y%m%d%H%M%S").replace(tzinfo=EAT)
	except ValueError:
		frappe.throw(_("Invalid transaction time"))
	age = datetime.now(EAT) - sent
	if age > MAX_AGE or age < -MAX_SKEW:
		frappe.throw(_("Transaction time is outside the accepted window"))
	return sent.astimezone(ZoneInfo(get_system_timezone())).replace(tzinfo=None)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="BusinessShortCode", limit=30, seconds=60, methods=["POST"])
def ingest_paybill(**payload):
	"""Daraja C2B confirmation URL: one unmatched inbox record per TransID, matched in the background."""
	payload.pop("cmd", None)
	payload.pop("token", None)  # form-encoded posts merge the query string into the payload
	shortcode = str(payload.get("BusinessShortCode") or "").strip()
	channel = paybill_channel(shortcode)
	trans_id = str(payload.get("TransID") or "").strip()
	user = frappe.session.user
	# The inbox reserves raw_payload for System Manager; the caller is authenticated by the token above.
	frappe.set_user("Administrator")
	try:
		if not trans_id:
			frappe.throw(_("Missing transaction code"))
		values = {
			"doctype": "Electronic Collection",
			"channel": channel,
			"transaction_code": trans_id,
			"amount": float(money(payload.get("TransAmount"))),
			"sender": " ".join(
				filter(
					None, (str(payload.get(k) or "").strip() for k in ("FirstName", "MiddleName", "LastName"))
				)
			)
			or payload.get("MSISDN"),
			# Never matches a Student ID, so a blank reference lands in Needs Review rather than being lost.
			"account_reference": str(payload.get("BillRefNumber") or "").strip() or "-",
			"received_at": paybill_time(payload.get("TransTime")),
			"raw_payload": json.dumps(payload, sort_keys=True),
		}
		if frappe.db.exists("Electronic Collection", {"transaction_code": trans_id}):
			paybill_log().info("Paybill replay ignored: TransID=%s", trans_id)
			return PAYBILL_ACK
		doc = frappe.get_doc(values).insert()
		# Matching needs the school settings and may fail; the record stays New for the Bursar if it does.
		frappe.enqueue(
			"frappe_education_kenya.collections.match",
			queue="short",
			enqueue_after_commit=True,
			name=doc.name,
		)
		return PAYBILL_ACK
	except frappe.UniqueValidationError:
		# A concurrent delivery of the same TransID won the insert.
		frappe.db.rollback()
		paybill_log().info("Paybill replay ignored: TransID=%s", trans_id)
		return PAYBILL_ACK
	except frappe.ValidationError as e:
		frappe.db.rollback()
		paybill_log().warning("Paybill callback rejected: TransID=%s reason=%s", trans_id, e)
		return PAYBILL_REJECT
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title=f"Paybill ingest failed: {trans_id}")
		return PAYBILL_REJECT
	finally:
		frappe.set_user(user)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="BusinessShortCode", limit=30, seconds=60, methods=["POST"])
def validate_paybill(**payload):
	"""Daraja C2B validation URL: unmatched references go to Bursar review, so every payment is accepted."""
	paybill_channel(str(payload.get("BusinessShortCode") or "").strip())
	return PAYBILL_ACK


@frappe.whitelist(methods=["POST"])
def match(name: str):
	gate("Electronic Collection", name)
	doc = frappe.get_doc("Electronic Collection", name, for_update=True)
	if doc.status not in ("New", "Needs Review", "Matched"):
		frappe.throw(_("Only unapproved collections can be matched"))
	# SQL collation may be case insensitive; Python equality enforces exact ID.
	student = frappe.db.get_value("Student", {"name": doc.account_reference}, "name")
	doc.student = student if student == doc.account_reference else None
	doc.sales_invoice = None
	doc.fees = None
	if doc.student:
		# Auto-match only one unambiguous standard target; otherwise leave for Bursar review.
		config = settings()
		base = {
			"company": config.company,
			"currency": config.default_currency,
			"docstatus": 1,
			"outstanding_amount": [">=", doc.amount],
		}
		customer = frappe.db.get_value("Student", doc.student, "customer")
		candidates = [
			("fees", n)
			for n in frappe.get_list(
				"Fees", filters={**base, "student": doc.student}, pluck="name", limit_page_length=2
			)
		]
		if customer:
			candidates += [
				("sales_invoice", n)
				for n in frappe.get_list(
					"Sales Invoice",
					filters={**base, "customer": customer, "is_return": 0},
					pluck="name",
					limit_page_length=2,
				)
			]
		if len(candidates) == 1:
			doc.set(*candidates[0])
	doc.flags.finance_action = True
	doc.workflow_state = "Matched" if doc.student and (doc.sales_invoice or doc.fees) else "Needs Review"
	doc.save()
	return {"ok": True, "name": doc.name, "message": _(doc.status)}


@frappe.whitelist(methods=["POST"])
def approve(name: str):
	gate("Electronic Collection", name)
	doc = frappe.get_doc("Electronic Collection", name, for_update=True)
	if doc.status == "Posted":
		return {"ok": True, "name": doc.payment_entry, "message": _("Already posted")}
	if doc.status != "Matched":
		frappe.throw(_("Match the student and invoice before approval"))
	doc.workflow_state = "Approved"
	doc.save()
	return {"ok": True, "name": doc.payment_entry, "message": _("Approved collection posted")}


@frappe.whitelist(methods=["POST"])
def reject(name: str, reason: str):
	gate("Electronic Collection", name)
	if not reason.strip():
		frappe.throw(_("A rejection reason is required"))
	doc = frappe.get_doc("Electronic Collection", name, for_update=True)
	if doc.status not in ("New", "Matched", "Needs Review"):
		frappe.throw(_("This collection cannot be rejected"))
	doc.rejection_reason = reason.strip()
	doc.workflow_state = "Rejected"
	doc.save()
	return {"ok": True, "name": doc.name, "message": _("Collection rejected")}


def post_approved(doc):
	gate("Electronic Collection", doc.name)
	locked = frappe.get_doc("Electronic Collection", doc.name, for_update=True)
	if locked.status != "Approved":
		return
	if locked.payment_entry:
		frappe.throw(_("Collection already has a Payment Entry"))
	channel = frappe.get_doc("Payment Channel", locked.channel)
	if not channel.enabled:
		frappe.throw(_("Payment channel is disabled"))
	target_type = "Fees" if locked.fees else "Sales Invoice"
	pe = make_payment(
		locked.student,
		locked.fees or locked.sales_invoice,
		locked.amount,
		channel.bank_account,
		target_type,
		channel.mode_of_payment,
	)
	pe.electronic_collection = locked.name
	pe.reference_no = locked.transaction_code
	pe.reference_date = locked.received_at
	pe.flags.finance_action = True
	pe.insert()
	locked.db_set("payment_entry", pe.name)
	frappe.has_permission("Payment Entry", "submit", doc=pe, throw=True)
	pe.submit()
	locked.db_set(
		{
			"workflow_state": "Posted",
			"status": "Posted",
			"approved_by": frappe.session.user,
			"approved_on": now_datetime(),
		}
	)
	doc.payment_entry = pe.name
	doc.status = doc.workflow_state = "Posted"


def validate_collection_payment(pe):
	doc = frappe.get_doc("Electronic Collection", pe.electronic_collection, for_update=True)
	if doc.status != "Approved" or (doc.payment_entry and doc.payment_entry != pe.name):
		frappe.throw(_("Collection must be explicitly approved before posting"))
	channel = frappe.get_doc("Payment Channel", doc.channel)
	config = settings()
	target_type = "Fees" if doc.fees else "Sales Invoice"
	target_name = doc.fees or doc.sales_invoice
	invoice = invoice_for(doc.student, target_name, config, target_type)
	party = doc.student if target_type == "Fees" else invoice.customer
	if (
		pe.party != party
		or pe.paid_to != channel.bank_account
		or pe.mode_of_payment != channel.mode_of_payment
		or money(pe.paid_amount) != money(doc.amount)
		or money(pe.received_amount) != money(doc.amount)
	):
		frappe.throw(_("Payment differs from the approved collection"))
	if (
		len(pe.references) != 1
		or pe.references[0].reference_doctype != target_type
		or pe.references[0].reference_name != target_name
		or money(pe.references[0].allocated_amount) != money(doc.amount)
	):
		frappe.throw(_("Payment references differ from the approved collection"))


def setup():
	load_workflow("electronic_collection")
