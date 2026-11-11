"""Permission-bound, paginated guardian self-service; no implicit student resolver."""

import frappe
from education.education.api import get_guardians_for_user, is_guardian_of
from frappe import _

from frappe_education_kenya.parent_ops import PURPOSES, guardian_student_link, linked_students


def require_student(student: str):
	if not isinstance(student, str) or not student or frappe.session.user == "Guest":
		frappe.throw(_("Please sign in to access your child's records."), frappe.PermissionError)
	user = frappe.session.user
	if not is_guardian_of(student, user) and not frappe.db.exists("Student", {"name": student, "user": user}):
		frappe.throw(_("You are not linked to this student."), frappe.PermissionError)
	frappe.has_permission("Student", "read", doc=student, throw=True)


def pagination(start=0, limit=20):
	if isinstance(start, bool) or isinstance(limit, bool):
		frappe.throw(_("Invalid page size."))
	try:
		start, limit = int(start), int(limit)
	except (TypeError, ValueError):
		frappe.throw(_("Invalid page size."))
	if start < 0 or not 1 <= limit <= 100:
		frappe.throw(_("Page size must be between 1 and 100; start cannot be negative."))
	return start, limit


def page(doctype, filters, fields, start, limit, order_by="creation desc, name desc"):
	start, limit = pagination(start, limit)
	rows = frappe.get_all(
		doctype,
		filters=filters,
		fields=fields,
		order_by=order_by,
		limit_start=start,
		limit_page_length=limit + 1,
	)
	return {"data": rows[:limit], "start": start, "limit": limit, "has_more": len(rows) > limit}


@frappe.whitelist(methods=["GET"])
def fee_statement(student: str, start: int = 0, limit: int = 20):
	require_student(student)
	return {
		"fees": page(
			"Fees",
			{"student": student, "docstatus": 1},
			["name", "posting_date", "due_date", "grand_total", "outstanding_amount", "currency"],
			start,
			limit,
		),
		"invoices": page(
			"Sales Invoice",
			{"student": student, "docstatus": 1},
			["name", "posting_date", "due_date", "grand_total", "outstanding_amount", "currency"],
			start,
			limit,
		),
	}


@frappe.whitelist(methods=["GET"])
def pledges(student: str, start: int = 0, limit: int = 20):
	require_student(student)
	return {
		"pledges": page(
			"Fee Pledge",
			{"student": student},
			["name", "amount", "due_date", "met_amount", "status"],
			start,
			limit,
		),
		"bursaries": page(
			"Bursary Award",
			{"student": student},
			["name", "amount", "allocated_amount", "valid_from", "valid_to", "workflow_state"],
			start,
			limit,
		),
	}


@frappe.whitelist(methods=["GET"])
def library_items(student: str, start: int = 0, limit: int = 20):
	require_student(student)
	return page(
		"Library Circulation",
		{"borrower_type": "Student", "borrower": student},
		["name", "copy", "issued_on", "due_on", "returned_on", "status", "fine_amount"],
		start,
		limit,
	)


@frappe.whitelist(methods=["GET"])
def timetable(student: str, start: int = 0, limit: int = 20):
	require_student(student)
	groups = frappe.get_all(
		"Student Group Student",
		filters={
			"student": student,
			"active": 1,
			"parenttype": "Student Group",
		},
		pluck="parent",
	)
	return page(
		"Course Schedule",
		{"student_group": ["in", groups or [""]], "docstatus": ["!=", 2]},
		["name", "course", "instructor_name", "schedule_date", "from_time", "to_time", "room"],
		start,
		limit,
		"schedule_date desc, from_time asc, name asc",
	)


@frappe.whitelist(methods=["GET"])
def results(student: str, start: int = 0, limit: int = 20):
	require_student(student)
	return page(
		"Assessment Result",
		{"student": student, "docstatus": 1, "kenya_guardian_published": 1},
		["name", "course", "academic_term", "assessment_group", "total_score", "maximum_score", "grade"],
		start,
		limit,
	)


@frappe.whitelist(methods=["POST"])
def set_consent(student: str, purpose: str, granted: bool):
	require_student(student)
	if not is_guardian_of(student, frappe.session.user):
		frappe.throw(_("Only a linked guardian can record consent."), frappe.PermissionError)
	if purpose not in PURPOSES or not isinstance(granted, bool):
		frappe.throw(_("Invalid consent decision."))
	guardians = [g for g in get_guardians_for_user() if guardian_student_link(g, student)]
	names = []
	for guardian in guardians:
		doc = frappe.get_doc(
			{
				"doctype": "Guardian Consent",
				"guardian": guardian,
				"student": student,
				"purpose": purpose,
				"status": "Granted" if granted else "Revoked",
				"captured_via": "Portal",
			}
		)
		frappe.has_permission("Guardian Consent", "create", doc=doc, throw=True)
		doc.insert()
		names.append(doc.name)
	return {"ok": True, "name": names[0], "message": _("Consent decision recorded.")}


@frappe.whitelist(methods=["POST"])
def choose_pathway(student: str, first: str, second: str = "", rationale: str = ""):
	require_student(student)
	frappe.has_permission("Student Pathway Choice", "create", throw=True)
	from frappe_education_kenya.pathways import choose_pathway as choose

	return choose(student, first, second, rationale)


@frappe.whitelist(methods=["POST"])
def submit_pathway(student: str, name: str):
	require_student(student)
	doc = frappe.get_doc("Student Pathway Choice", name)
	if doc.student != student or doc.workflow_state != "Draft":
		frappe.throw(_("Only this student's draft choice can be submitted."), frappe.PermissionError)
	frappe.has_permission("Student Pathway Choice", "write", doc=doc, throw=True)
	from frappe.model.workflow import apply_workflow

	apply_workflow(doc, "Submit Choice")
	return {"ok": True, "name": doc.name, "message": _("Pathway choice submitted for approval.")}


def linked_children():
	names = linked_students()
	if not names:
		return []
	return frappe.get_all(
		"Student",
		filters={"name": ["in", names]},
		fields=["name", "student_name"],
		order_by="student_name asc",
	)
