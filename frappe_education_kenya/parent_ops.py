"""Append-only guardian consent and authenticated login audit."""

import frappe
from education.education.api import get_guardians_for_user, is_guardian_of
from frappe import _
from frappe.utils import now_datetime

PURPOSES = ("Messaging", "Photo", "Trip", "Data Sharing")
STAFF = {"System Manager", "Bursar", "Head Teacher", "Academic Admin"}


def has_messaging_consent(guardian: str, student: str) -> bool:
	if not isinstance(guardian, str) or not isinstance(student, str):
		return False
	rows = frappe.get_all(
		"Guardian Consent",
		filters={"guardian": guardian, "student": student, "purpose": "Messaging"},
		fields=["status"],
		order_by="captured_on desc, creation desc, name desc",
		limit_page_length=1,
	)
	return bool(rows and rows[0].status == "Granted")


def guardian_student_link(guardian, student):
	return bool(
		frappe.db.exists(
			"Student Guardian",
			{
				"parent": student,
				"parenttype": "Student",
				"guardian": guardian,
			},
		)
	)


def guardian_students(user=None):
	"""Students whose Student Guardian rows point at one of the user's Guardian records."""
	guardians = get_guardians_for_user(user)
	if not guardians:
		return []
	return frappe.get_all(
		"Student Guardian",
		filters={"parenttype": "Student", "guardian": ["in", guardians]},
		pluck="parent",
		distinct=True,
	)


def linked_students(user=None):
	"""The user's own Student record plus every ward they are a guardian of."""
	user = user or frappe.session.user
	if user == "Guest":
		return []
	own = frappe.get_all("Student", filters={"user": user}, pluck="name")
	return sorted({*own, *guardian_students(user)})


def consent_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True
	if set(frappe.get_roles(user)) & (STAFF - {"System Manager"}):
		return ptype in (None, "read", "report", "export", "print", "select")
	return (
		doc.guardian in get_guardians_for_user(user)
		and is_guardian_of(doc.student, user)
		and guardian_student_link(doc.guardian, doc.student)
	)


def consent_query(user=None):
	user = user or frappe.session.user
	if user == "Administrator" or set(frappe.get_roles(user)) & STAFF:
		return ""
	guardians = get_guardians_for_user(user)
	if not guardians:
		return "1=0"
	consent = frappe.qb.DocType("Guardian Consent")
	link = frappe.qb.DocType("Student Guardian")
	allowed = (
		frappe.qb.from_(link)
		.select(link.parent)
		.where((link.guardian == consent.guardian) & (link.parenttype == "Student"))
	)
	return ((consent.guardian.isin(guardians)) & consent.student.isin(allowed)).get_sql()


def validate_consent(doc):
	if not doc.is_new():
		frappe.throw(_("Consent history cannot be edited. Create a new consent decision."))
	if doc.purpose not in PURPOSES or doc.status not in ("Granted", "Revoked"):
		frappe.throw(_("Invalid consent decision."))
	if not guardian_student_link(doc.guardian, doc.student):
		frappe.throw(_("Guardian is not linked to this student."), frappe.PermissionError)
	user = frappe.session.user
	if user != "Administrator" and "System Manager" not in frappe.get_roles(user):
		if doc.guardian not in get_guardians_for_user(user) or not is_guardian_of(doc.student, user):
			frappe.throw(_("You may only record consent for your linked children."), frappe.PermissionError)
		if doc.captured_via != "Portal":
			frappe.throw(_("Guardians must record consent through the portal."), frappe.PermissionError)
	if doc.captured_via not in ("Portal", "Paper"):
		frappe.throw(_("USSD consent is unavailable until an aggregator is configured."))
	doc.captured_on = now_datetime()
	doc.revoked_on = doc.captured_on if doc.status == "Revoked" else None


def on_session_creation(login_manager):
	user = login_manager.user
	for guardian in get_guardians_for_user(user):
		# Trusted login hook only: users cannot author or alter audit records.
		doc = frappe.get_doc(
			{
				"doctype": "Parent Login Log",
				"guardian": guardian,
				"user": user,
				"logged_in_at": now_datetime(),
				"ip": getattr(frappe.local, "request_ip", None),
			}
		)
		doc.flags.from_guardian_login = True
		doc.insert(ignore_permissions=True)


def validate_result_publication(doc, method=None):
	old = doc.get_doc_before_save()
	changed = (
		bool(doc.get("kenya_guardian_published"))
		if not old
		else (doc.get("kenya_guardian_published") != old.get("kenya_guardian_published"))
	)
	if changed:
		frappe.only_for(["System Manager", "Academic Admin", "Head Teacher"])


def setup():
	"""Called by the app's install/after_migrate integration, never at import."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(
		{
			"Assessment Result": [
				{
					"fieldname": "kenya_guardian_published",
					"label": "Guardian Published",
					"fieldtype": "Check",
					"default": "0",
					"insert_after": "grade",
					"allow_on_submit": 1,
					"permlevel": 1,
					"description": "Release submitted results to linked guardians and the student.",
				}
			]
		}
	)
