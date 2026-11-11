"""CBC choice, consent and placement rules; the choice is the placement authority."""

import hashlib
import json
from pathlib import Path

import frappe
from education.education.api import get_guardians_for_user, is_guardian_of
from frappe import _
from frappe.utils import cint

CHOICE = "Student Pathway Choice"
COMBINATION = "CBC Subject Combination"
REVIEW_ROLES = {"Academic Admin", "Head Teacher"}
READ_ROLES = REVIEW_ROLES | {"Instructor"}
CHOICE_FIELDS = ("student", "academic_year", "first_choice", "second_choice", "rationale")
AUDIT_FIELDS = ("approved_by", "placed_by", "override_by")


def current_academic_year():
	year = frappe.db.get_single_value("Education Settings", "current_academic_year")
	if not year:
		frappe.throw(_("Set the Current Academic Year in Education Settings first."))
	return year


def is_linked_student(student, user=None):
	user = user or frappe.session.user
	if not user or user == "Guest" or not student:
		return False
	return frappe.db.get_value("Student", student, "user") == user or is_guardian_of(student, user)


def choice_has_permission(doc, ptype=None, user=None, **kwargs):
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator":
		return True
	if ptype in ("read", "select", "print", "report", "email", None):
		return bool(roles & READ_ROLES) or is_linked_student(doc.get("student"), user)
	if ptype == "create":
		return bool(roles & {"Guardian", "Student"}) and (
			not doc.get("student") or is_linked_student(doc.student, user)
		)
	if ptype != "write":
		return False
	stored_state = frappe.db.get_value(CHOICE, doc.name, "workflow_state") if not doc.is_new() else "Draft"
	if stored_state == "Placed":
		return False
	if roles & REVIEW_ROLES:
		return True
	return stored_state == "Draft" and is_linked_student(doc.get("student"), user)


def choice_query_conditions(user=None):
	user = user or frappe.session.user
	if user == "Administrator" or set(frappe.get_roles(user)) & READ_ROLES:
		return ""
	if not user or user == "Guest":
		return "1=0"
	choice = frappe.qb.DocType(CHOICE)
	student = frappe.qb.DocType("Student")
	link = frappe.qb.DocType("Student Guardian")
	own = frappe.qb.from_(student).select(student.name).where(student.user == user)
	condition = choice.student.isin(own)
	guardians = get_guardians_for_user(user)
	if guardians:
		linked = (
			frappe.qb.from_(link)
			.select(link.parent)
			.where((link.parenttype == "Student") & link.guardian.isin(guardians))
		)
		condition |= choice.student.isin(linked)
	return condition.get_sql(quote_char="`")


def active_guardian_consent(student):
	"""Use the latest Data Sharing decision for each genuinely linked guardian."""
	guardians = frappe.get_all(
		"Student Guardian", filters={"parent": student, "parenttype": "Student"}, pluck="guardian"
	)
	if not guardians:
		return None
	consents = frappe.get_all(
		"Guardian Consent",
		filters={"student": student, "guardian": ["in", guardians], "purpose": "Data Sharing"},
		fields=["name", "guardian", "status"],
		order_by="captured_on desc, creation desc, name desc",
	)
	seen = set()
	for consent in consents:
		if consent.guardian in seen:
			continue
		seen.add(consent.guardian)
		if consent.status == "Granted":
			return consent.name
	return None


def validate_pathway(doc):
	labels = set()
	for track in doc.get("tracks") or []:
		track.track_name = (track.track_name or "").strip()
		key = track.track_name.casefold()
		if not key or key in labels:
			frappe.throw(_("Track labels must be non-empty and unique within a pathway."))
		labels.add(key)
	if not doc.is_new():
		for combination in frappe.get_all(
			COMBINATION, filters={"pathway": doc.name}, fields=["track", "enabled"]
		):
			track = next((row for row in doc.tracks if row.track_name == combination.track), None)
			if not track or (combination.enabled and not track.is_confirmed):
				frappe.throw(
					_("Update combinations using a track before renaming, removing or unconfirming it.")
				)


def validate_combination(doc):
	if cint(doc.capacity) < 0:
		frappe.throw(_("Capacity cannot be negative."))
	doc.track = (doc.track or "").strip()
	pathway = frappe.get_doc("CBC Pathway", doc.pathway)
	track = next((row for row in pathway.tracks if row.track_name == doc.track), None)
	if not track:
		frappe.throw(_("Select a track belonging to this pathway."))
	if doc.enabled and not track.is_confirmed:
		frappe.throw(_("Confirm the draft track label with the school before enabling this combination."))
	courses = [row.course for row in doc.get("subjects") or []]
	if not courses or not all(courses) or len(set(courses)) != len(courses):
		frappe.throw(_("A combination needs distinct subjects with a course on every row."))
	if any(row.kind not in ("Core", "Elective") for row in doc.subjects):
		frappe.throw(_("Every combination subject must be Core or Elective."))
	if doc.is_new():
		return
	frappe.db.get_value(COMBINATION, doc.name, "name", for_update=True)
	before = doc.get_doc_before_save()
	choice = frappe.qb.DocType(CHOICE)
	used = (
		frappe.qb.from_(choice)
		.select(choice.name)
		.where(
			(choice.first_choice == doc.name)
			| (choice.second_choice == doc.name)
			| (choice.placement == doc.name)
		)
		.where(choice.workflow_state.isin(["Submitted", "Approved", "Placed"]))
		.limit(1)
		.for_update()
	).run()
	if used and before:
		old_subjects = [(row.course, row.kind) for row in before.subjects]
		new_subjects = [(row.course, row.kind) for row in doc.subjects]
		if before.pathway != doc.pathway or before.track != doc.track or old_subjects != new_subjects:
			frappe.throw(
				_(
					"A submitted choice uses this combination. Create a new combination to change its subjects or track."
				)
			)
	if before and cint(before.capacity) != cint(doc.capacity):
		from frappe.query_builder.functions import Count

		counts = (
			frappe.qb.from_(choice)
			.select(Count(choice.name).as_("placed"))
			.where((choice.placement == doc.name) & (choice.workflow_state == "Placed"))
			.groupby(choice.academic_year)
		).run(as_dict=True)
		if any(row.placed > cint(doc.capacity) for row in counts):
			frappe.throw(_("Capacity cannot be reduced below an existing year's placed count."))


def _enabled_combination(name, *, for_update=False):
	combination = frappe.get_doc(COMBINATION, name, for_update=for_update)
	if not combination.enabled:
		frappe.throw(_("The selected subject combination is not available."))
	pathway = frappe.get_doc("CBC Pathway", combination.pathway)
	if not any(row.track_name == combination.track and row.is_confirmed for row in pathway.tracks):
		frappe.throw(_("The combination must use a confirmed track in its pathway."))
	return combination


def _validate_transition(doc, before, roles):
	old_state = before.workflow_state if before else "Draft"
	state = doc.workflow_state or "Draft"
	if not before and state != "Draft":
		frappe.throw(_("New pathway choices must start in Draft."))
	if old_state == "Placed":
		frappe.throw(_("A placed choice is the authoritative placement and cannot be edited."))
	if state != old_state:
		allowed = {
			("Draft", "Submitted"): {"Guardian", "Student"},
			("Submitted", "Approved"): {"Academic Admin"},
			("Submitted", "Rejected"): {"Academic Admin"},
			("Approved", "Placed"): REVIEW_ROLES,
			("Rejected", "Placed"): {"Head Teacher"},
		}
		if not roles & allowed.get((old_state, state), set()):
			frappe.throw(_("You cannot perform this pathway workflow transition."), frappe.PermissionError)
	if old_state == "Draft":
		if not is_linked_student(doc.student):
			frappe.throw(
				_("Only the student or a linked guardian may edit or submit this choice."),
				frappe.PermissionError,
			)
	elif any(doc.get(field) != before.get(field) for field in CHOICE_FIELDS):
		frappe.throw(_("Student choices cannot be changed after submission."), frappe.PermissionError)
	return old_state, state


def validate_choice(doc):
	doc.academic_year = doc.academic_year or current_academic_year()
	doc.workflow_state = doc.workflow_state or "Draft"
	before = doc.get_doc_before_save()
	roles = set(frappe.get_roles())
	old_state, state = _validate_transition(doc, before, roles)
	if before and any(doc.get(field) != before.get(field) for field in ("student", "academic_year")):
		frappe.throw(_("Student and academic year cannot be changed."))
	if not before or old_state == "Draft":
		if doc.academic_year != current_academic_year():
			frappe.throw(_("New or draft choices must use the current academic year."))
	# Lock the stable parent, including when no choice row exists yet.
	student = frappe.db.get_value(
		"Student", doc.student, ["name", "kenya_kjsea_score"], as_dict=True, for_update=True
	)
	if not student:
		frappe.throw(_("Student does not exist."))
	if before and old_state != "Draft":
		if doc.kjsea_basis != before.kjsea_basis:
			frappe.throw(_("KJSEA basis is protected."), frappe.PermissionError)
	else:
		doc.kjsea_basis = student.kenya_kjsea_score
	for field in AUDIT_FIELDS:
		if doc.get(field) != (before.get(field) if before else None):
			frappe.throw(_("Approval and placement audit fields are server managed."), frappe.PermissionError)
	if state != "Rejected":
		choice = frappe.qb.DocType(CHOICE)
		duplicates = (
			frappe.qb.from_(choice)
			.select(choice.name)
			.where((choice.student == doc.student) & (choice.academic_year == doc.academic_year))
			.where(choice.workflow_state != "Rejected")
			.where(choice.name != (doc.name or ""))
			.for_update()
		).run()
		if duplicates:
			frappe.throw(_("Only one active pathway choice is allowed per student and academic year."))
		doc.active_key = hashlib.sha256(json.dumps([doc.student, doc.academic_year]).encode()).hexdigest()
	else:
		doc.active_key = None
	if doc.second_choice and doc.first_choice == doc.second_choice:
		frappe.throw(_("First and second choices must be different combinations."))
	if not doc.first_choice:
		frappe.throw(_("A first-choice combination is required."))
	for name in (doc.first_choice, doc.second_choice):
		if name:
			_enabled_combination(name)
	consent = active_guardian_consent(doc.student)
	doc.guardian_consent_record = consent
	doc.guardian_consent = int(bool(consent))
	if state not in ("Draft", "Rejected") and not consent:
		frappe.throw(
			_("A linked guardian's active Data Sharing consent is required before submission or placement.")
		)
	if state == "Approved" and old_state != state:
		doc.approved_by = frappe.session.user
	if state != "Placed":
		if doc.placement or doc.override_reason or doc.override_by:
			if old_state not in ("Approved", "Rejected") or not roles & REVIEW_ROLES:
				frappe.throw(
					_("Only reviewers may prepare placement details after review."), frappe.PermissionError
				)
		if doc.override_reason and "Head Teacher" not in roles:
			frappe.throw(
				_("Only the Head Teacher may give a placement override reason."), frappe.PermissionError
			)
		return
	if not doc.placement:
		frappe.throw(_("Select a placement combination first."))
	# Every placement path (native Workflow, REST save or portal) takes this same lock.
	combination = _enabled_combination(doc.placement, for_update=True)
	choice = frappe.qb.DocType(CHOICE)
	placed = (
		frappe.qb.from_(choice)
		.select(choice.name)
		.where((choice.placement == doc.placement) & (choice.academic_year == doc.academic_year))
		.where((choice.workflow_state == "Placed") & (choice.name != doc.name))
		.for_update()
	).run()
	override = "Head Teacher" in roles and bool((doc.override_reason or "").strip())
	if "Academic Admin" not in roles and not override:
		frappe.throw(_("Head Teacher override placement requires a reason."), frappe.PermissionError)
	if (
		old_state == "Rejected"
		or len(placed) >= cint(combination.capacity)
		or doc.placement not in (doc.first_choice, doc.second_choice)
	) and not override:
		frappe.throw(_("This placement requires a Head Teacher override with a reason."))
	if doc.override_reason and not override:
		frappe.throw(_("Only the Head Teacher may override placement."), frappe.PermissionError)
	doc.override_reason = (doc.override_reason or "").strip()
	doc.override_by = frappe.session.user if override else None
	doc.placed_by = frappe.session.user


@frappe.whitelist(methods=["GET"])
def get_current_academic_year():
	frappe.has_permission(COMBINATION, "read", throw=True)
	return {"academic_year": current_academic_year()}


@frappe.whitelist(methods=["POST"])
def choose_pathway(student: str, first: str, second: str | None = None, rationale: str = ""):
	for value in (student, first):
		if not isinstance(value, str) or not value.strip():
			frappe.throw(_("Student and first choice must be non-empty names."))
	if (second is not None and not isinstance(second, str)) or not isinstance(rationale, str):
		frappe.throw(_("Invalid pathway choice input."))
	frappe.only_for(["Guardian", "Student"])
	if not is_linked_student(student):
		frappe.throw(_("This student is not linked to your account."), frappe.PermissionError)
	year = current_academic_year()
	frappe.db.get_value("Student", student, "name", for_update=True)
	choice = frappe.qb.DocType(CHOICE)
	rows = (
		frappe.qb.from_(choice)
		.select(choice.name, choice.workflow_state)
		.where((choice.student == student) & (choice.academic_year == year))
		.where(choice.workflow_state != "Rejected")
		.for_update()
	).run(as_dict=True)
	if rows:
		if rows[0].workflow_state != "Draft":
			frappe.throw(_("Your pathway choice has already been submitted and is read-only."))
		doc = frappe.get_doc(CHOICE, rows[0].name)
		frappe.has_permission(CHOICE, "write", doc=doc, throw=True)
	else:
		doc = frappe.new_doc(CHOICE)
		doc.student = student
		doc.academic_year = year
		frappe.has_permission(CHOICE, "create", doc=doc, throw=True)
	doc.first_choice = first
	doc.second_choice = second or None
	doc.rationale = rationale
	doc.save()
	return {
		"ok": True,
		"name": doc.name,
		"message": _("Pathway choice saved as Draft. Submit it using the workflow after guardian consent."),
	}


def setup():
	"""Idempotent after-migrate setup; never confirms unverified track labels."""
	frappe.only_for("System Manager")
	pathways = {
		"STEM": [
			"Pure Sciences",
			"Applied Sciences",
			"Technical and Engineering",
			"Career and Technology Studies",
		],
		"Social Sciences": ["Humanities and Business Studies", "Languages and Literature"],
		"Arts and Sports": ["Arts", "Sports Science"],
	}
	for name, tracks in pathways.items():
		if not frappe.db.exists("CBC Pathway", name):
			frappe.get_doc(
				{
					"doctype": "CBC Pathway",
					"pathway_name": name,
					"tracks": [{"track_name": label, "is_confirmed": 0} for label in tracks],
				}
			).insert()
	workflow = json.loads((Path(__file__).parent / "fixtures" / "cbc_pathways_workflow.json").read_text())
	for state in workflow["states"]:
		if not frappe.db.exists("Workflow State", state["state"]):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state["state"]}).insert()
	for action in {row["action"] for row in workflow["transitions"]}:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert()
	# fixtures/ is re-imported by every migrate; setup only bootstraps a missing workflow.
	if not frappe.db.exists("Workflow", workflow["name"]):
		frappe.get_doc(workflow).insert()
