"""Consent-aware SMS dispatch. Disabled unless Education Kenya Settings enables scheduled messages."""

import json
import math

import frappe
from frappe import _
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.utils import cint, get_datetime, now_datetime

from frappe_education_kenya.parent_ops import guardian_student_link, has_messaging_consent

ROLES = ["System Manager", "Bursar", "Head Teacher", "Academic Admin"]


def dispatch_enabled():
	return bool(cint(frappe.db.get_single_value("Education Kenya Settings", "enable_scheduled_messages")))


def validated_filters(audience, raw):
	try:
		filters = json.loads(raw) if isinstance(raw, str) else raw
	except (TypeError, ValueError):
		frappe.throw(_("Audience filters must be a JSON object."))
	if not isinstance(filters, dict):
		frappe.throw(_("Audience filters must be a JSON object."))
	if audience == "Class":
		if set(filters) != {"student_group"} or not isinstance(filters["student_group"], str):
			frappe.throw(_("Class requires a student_group string."))
		if not frappe.db.exists("Student Group", filters["student_group"]):
			frappe.throw(_("Student group does not exist."))
	elif audience == "Fees Balance":
		if set(filters) - {"minimum_balance", "company"} or "minimum_balance" not in filters:
			frappe.throw(_("Fees Balance requires minimum_balance and optional company."))
		amount = filters["minimum_balance"]
		if (
			isinstance(amount, bool)
			or not isinstance(amount, (int, float))
			or not math.isfinite(amount)
			or amount <= 0
		):
			frappe.throw(_("Minimum balance must be a positive number."))
		if "company" in filters and (
			not isinstance(filters["company"], str) or not frappe.db.exists("Company", filters["company"])
		):
			frappe.throw(_("Invalid company."))
	elif audience == "Guardian List":
		guardians = filters.get("guardians")
		if set(filters) != {"guardians"} or not isinstance(guardians, list) or not guardians:
			frappe.throw(_("Guardian List requires a non-empty guardians list."))
		if len(guardians) > 1000 or any(not isinstance(g, str) or not g for g in guardians):
			frappe.throw(_("Choose between 1 and 1000 guardian IDs."))
		if frappe.db.count("Guardian", {"name": ["in", set(guardians)]}) != len(set(guardians)):
			frappe.throw(_("An audience guardian does not exist."))
	else:
		frappe.throw(_("Invalid audience."))
	return filters


def audience_pairs(audience, filters):
	if audience == "Guardian List":
		links = {"guardian": ["in", filters["guardians"]]}
	else:
		if audience == "Class":
			students = frappe.get_all(
				"Student Group Student",
				filters={"parent": filters["student_group"], "parenttype": "Student Group", "active": 1},
				pluck="student",
			)
		else:
			fee_filters = {"docstatus": 1, "outstanding_amount": [">=", filters["minimum_balance"]]}
			if filters.get("company"):
				fee_filters["company"] = filters["company"]
			students = frappe.get_all("Fees", filters=fee_filters, pluck="student")
			students += frappe.get_all("Sales Invoice", filters=fee_filters, pluck="student")
		links = {"parent": ["in", [s for s in set(students) if s] or [""]]}
	links["parenttype"] = "Student"
	rows = frappe.get_all("Student Guardian", filters=links, fields=["guardian", "parent"])
	return sorted({(r.guardian, r.parent) for r in rows if r.guardian})


def validate_message(doc):
	validated_filters(doc.audience, doc.filters)
	if not doc.body or not doc.body.strip():
		frappe.throw(_("Message body is required."))
	old = doc.get_doc_before_save()
	if old and old.status != "Draft" and not doc.flags.guardian_dispatch:
		frappe.throw(_("Scheduled and dispatched messages cannot be edited."))
	if not doc.flags.guardian_dispatch and (doc.status not in (None, "", "Draft") or doc.recipients):
		frappe.throw(_("Use Schedule to build the recipient list."))
	doc.status = doc.status or "Draft"


@frappe.whitelist(methods=["POST"])
def schedule(name: str):
	frappe.only_for(ROLES)
	frappe.has_permission("Scheduled Message", "write", doc=name, throw=True)
	lock = frappe.qb.DocType("Scheduled Message")
	frappe.qb.from_(lock).select(lock.name).where(lock.name == name).for_update().run()
	doc = frappe.get_doc("Scheduled Message", name)
	if doc.status != "Draft" or get_datetime(doc.send_at) <= now_datetime():
		frappe.throw(_("Only draft messages with a future send time can be scheduled."))
	filters = validated_filters(doc.audience, doc.filters)
	pairs = audience_pairs(doc.audience, filters)
	if not pairs:
		frappe.throw(_("No linked guardians match the audience."))
	mobiles = {
		r.name: r.mobile_number
		for r in frappe.get_all(
			"Guardian",
			filters={"name": ["in", sorted({g for g, _s in pairs})]},
			fields=["name", "mobile_number"],
		)
	}
	doc.set("recipients", [])
	for guardian, student in pairs:
		doc.append(
			"recipients",
			{"guardian": guardian, "student": student, "mobile": mobiles.get(guardian), "result": "Pending"},
		)
	doc.status = "Scheduled"
	doc.flags.guardian_dispatch = True
	doc.save()
	return {
		"ok": True,
		"name": doc.name,
		"message": _("Message scheduled. Dispatch requires explicit site configuration."),
	}


def dispatch_due():
	if not dispatch_enabled():
		return
	# The scheduler already executes as Administrator. Do not change request identity.
	for name in frappe.get_all(
		"Scheduled Message",
		filters={"status": "Scheduled", "send_at": ["<=", now_datetime()]},
		pluck="name",
		order_by="send_at asc",
		limit_page_length=100,
	):
		dispatch_message(name)


def dispatch_message(name):
	if not dispatch_enabled():
		return
	frappe.only_for(ROLES)
	frappe.has_permission("Scheduled Message", "write", doc=name, throw=True)
	lock = frappe.qb.DocType("Scheduled Message")
	frappe.qb.from_(lock).select(lock.name).where(lock.name == name).for_update().run()
	doc = frappe.get_doc("Scheduled Message", name)
	if doc.status != "Scheduled" or get_datetime(doc.send_at) > now_datetime():
		return
	doc.flags.guardian_dispatch = True
	doc.status = "Sending"
	doc.save()
	failed = False
	for row in doc.recipients:
		if row.result != "Pending":
			continue
		mobile = frappe.db.get_value("Guardian", row.guardian, "mobile_number")
		row.mobile = mobile
		if not mobile:
			row.result = "Skipped: no mobile number"
			continue
		if not guardian_student_link(row.guardian, row.student):
			row.result = "Skipped: guardian unlinked"
			continue
		if not frappe.db.get_single_value("SMS Settings", "sms_gateway_url") and not frappe.get_hooks(
			"send_sms"
		):
			row.result = "Failed: SMS gateway not configured"
			failed = True
			continue
		# Read latest consent immediately before each external call, never a cached audience decision.
		if not has_messaging_consent(row.guardian, row.student):
			row.result = "Skipped: no active consent"
			continue
		try:
			send_sms([mobile], doc.body, success_msg=False)
			# Core returns no delivery receipt; this is not a claim of handset delivery.
			row.result = "Submitted to gateway"
		except Exception:
			frappe.log_error(title=_("Scheduled guardian message failed"))
			row.result = "Failed: gateway error"
			failed = True
	doc.status = "Failed" if failed else "Sent"
	doc.save()
