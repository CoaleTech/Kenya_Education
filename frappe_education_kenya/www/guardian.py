"""Server-rendered self-service, sharing the same authorization as RPCs."""

from urllib.parse import urlencode

import frappe
from education.education.api import get_guardians_for_user, is_guardian_of
from frappe import _
from frappe.sessions import get_csrf_token

from frappe_education_kenya import portal
from frappe_education_kenya.parent_ops import PURPOSES, guardian_student_link

no_cache = 1
sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.title = _("Guardian self-service")
	context.children = portal.linked_children()
	context.signed_in = frappe.session.user != "Guest"
	context.student = None
	context.error = None
	context.notice = None
	if not context.children:
		return context
	student = frappe.form_dict.get("student") or context.children[0].name
	portal.require_student(student)
	context.student = student
	context.student_name = next(c.student_name for c in context.children if c.name == student)
	context.csrf_token = get_csrf_token()
	context.is_guardian = is_guardian_of(student, frappe.session.user)
	context.tab = frappe.form_dict.get("tab", "fees")
	tabs = {
		"fees": _("Fees"),
		"pledges": _("Pledges and bursaries"),
		"library": _("Library"),
		"timetable": _("Timetable"),
		"results": _("Published results"),
		"consent": _("Consent"),
		"pathway": _("Pathways"),
	}
	if context.tab not in tabs:
		frappe.throw(_("Invalid section."))
	context.tabs = [
		{"key": key, "label": label, "url": "/guardian?" + urlencode({"student": student, "tab": key})}
		for key, label in tabs.items()
	]
	if frappe.request and frappe.request.method == "POST":
		frappe.db.savepoint("guardian_action")
		try:
			context.notice = perform_action(student)["message"]
		except (frappe.ValidationError, frappe.PermissionError) as exc:
			frappe.db.rollback(save_point="guardian_action")
			context.error = str(exc)
	context.sections = []
	start, limit = portal.pagination(frappe.form_dict.get("start", 0), 20)
	context.start = start
	context.prev_url = "/guardian?" + urlencode(
		{"student": student, "tab": context.tab, "start": max(0, start - limit)}
	)
	context.next_url = "/guardian?" + urlencode(
		{"student": student, "tab": context.tab, "start": start + limit}
	)
	context.has_more = False
	if context.tab == "fees":
		data = portal.fee_statement(student, start, limit)
		for key, title in (("fees", _("School fees")), ("invoices", _("Invoices"))):
			add_section(
				context,
				title,
				data[key],
				[
					("name", _("Reference"), "Data"),
					("posting_date", _("Date"), "Date"),
					("due_date", _("Due"), "Date"),
					("grand_total", _("Amount"), "Currency"),
					("outstanding_amount", _("Balance"), "Currency"),
				],
			)
	elif context.tab == "pledges":
		data = portal.pledges(student, start, limit)
		add_section(
			context,
			_("Fee pledges"),
			data["pledges"],
			[
				("name", _("Reference"), "Data"),
				("amount", _("Amount"), "Currency"),
				("met_amount", _("Met"), "Currency"),
				("due_date", _("Due"), "Date"),
				("status", _("Status"), "Data"),
			],
		)
		add_section(
			context,
			_("Bursary awards"),
			data["bursaries"],
			[
				("name", _("Reference"), "Data"),
				("amount", _("Amount"), "Currency"),
				("allocated_amount", _("Allocated"), "Currency"),
				("valid_to", _("Valid until"), "Date"),
				("workflow_state", _("Status"), "Data"),
			],
		)
	elif context.tab == "library":
		add_section(
			context,
			_("Borrowed library items"),
			portal.library_items(student, start, limit),
			[
				("copy", _("Copy"), "Data"),
				("due_on", _("Due"), "Date"),
				("returned_on", _("Returned"), "Date"),
				("status", _("Status"), "Data"),
				("fine_amount", _("Fine"), "Currency"),
			],
		)
	elif context.tab == "timetable":
		add_section(
			context,
			_("Class timetable"),
			portal.timetable(student, start, limit),
			[
				("course", _("Course"), "Data"),
				("schedule_date", _("Date"), "Date"),
				("from_time", _("From"), "Time"),
				("to_time", _("To"), "Time"),
				("room", _("Room"), "Data"),
			],
		)
	elif context.tab == "results":
		add_section(
			context,
			_("Published results"),
			portal.results(student, start, limit),
			[
				("course", _("Course"), "Data"),
				("academic_term", _("Term"), "Data"),
				("total_score", _("Score"), "Float"),
				("maximum_score", _("Maximum"), "Float"),
				("grade", _("Grade"), "Data"),
			],
		)
	elif context.tab == "consent":
		context.consent = []
		for guardian in get_guardians_for_user():
			if not guardian_student_link(guardian, student):
				continue
			for purpose in PURPOSES:
				rows = frappe.get_all(
					"Guardian Consent",
					filters={"guardian": guardian, "student": student, "purpose": purpose},
					fields=["status", "captured_on"],
					order_by="captured_on desc, creation desc, name desc",
					limit_page_length=1,
				)
				context.consent.append(
					{
						"guardian": guardian,
						"purpose": purpose,
						"status": rows[0].status if rows else _("Not granted"),
					}
				)
	elif context.tab == "pathway":
		from frappe_education_kenya.pathways import current_academic_year

		context.choices = frappe.get_all(
			"Student Pathway Choice",
			filters={"student": student, "academic_year": current_academic_year()},
			fields=["name", "first_choice", "second_choice", "rationale", "workflow_state"],
			order_by="creation desc",
			limit_page_length=1,
		)
		context.choice = context.choices[0] if context.choices else None
		context.can_edit_choice = not context.choice or context.choice.workflow_state == "Draft"
		# Catalogue names only, shown after require_student; choose_pathway re-validates and authorizes.
		context.combinations = frappe.get_all(
			"CBC Subject Combination", filters={"enabled": 1}, fields=["name"], order_by="name asc"
		)
	return context


def add_section(context, title, data, columns):
	context.has_more = context.has_more or data["has_more"]
	context.sections.append({"title": title, "rows": data["data"], "columns": columns})


def perform_action(student):
	action = frappe.form_dict.get("action")
	if action == "consent":
		granted = frappe.form_dict.get("granted")
		if granted not in ("0", "1"):
			frappe.throw(_("Choose grant or revoke."))
		return portal.set_consent(student, frappe.form_dict.get("purpose"), granted == "1")
	if action == "pathway":
		return portal.choose_pathway(
			student,
			frappe.form_dict.get("first", ""),
			frappe.form_dict.get("second", ""),
			frappe.form_dict.get("rationale", ""),
		)
	if action == "submit_pathway":
		return portal.submit_pathway(student, frappe.form_dict.get("choice", ""))
	frappe.throw(_("Invalid action."))
