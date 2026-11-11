"""Deterministic weekly timetabling and guarded term publication (v16)."""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import timedelta

import frappe

from frappe_education_kenya.frappe_education_kenya.doctype.timetable_run.generator import (
	DAYS,
	overlaps,
	seconds,
	solve,
)

_run_action = ContextVar("timetable_run_action", default=False)
_publishing = ContextVar("timetable_publishing", default=False)


@contextmanager
def _action(marker):
	token = marker.set(True)
	try:
		yield
	finally:
		marker.reset(token)


def _guard(run, permission="write"):
	if not isinstance(run, str) or not run.strip():
		frappe.throw(frappe._("A Timetable Run name is required"))
	frappe.only_for("Academic Admin")
	frappe.has_permission("Timetable Run", permission, doc=run, throw=True)


def setup():
	"""Called by the app's installation/migration owner, never a public RPC."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(
		{
			"Course Schedule": [
				{
					"fieldname": "timetable_run",
					"label": "Timetable Run",
					"fieldtype": "Link",
					"options": "Timetable Run",
					"read_only": 1,
					"no_copy": 1,
					"insert_after": "title",
					"search_index": 1,
				}
			]
		}
	)
	frappe.db.add_unique("Timetable Period", ["day", "start_time"], "unique_timetable_day_start")


def _whole(value, minimum):
	"""Strict Int parsing for REST payloads; Frappe does not coerce before validate."""
	try:
		number = int(value)
		return number if number == float(value) and number >= minimum else None
	except (TypeError, ValueError):
		return None


def validate_period(doc):
	try:
		valid = doc.day in DAYS and seconds(doc.start_time) < seconds(doc.end_time)
	except (TypeError, ValueError):
		valid = False
	if not valid:
		frappe.throw(frappe._("Select a valid day and an end time after the start time"))


def validate_requirement(doc):
	for key in ("lessons_per_week", "max_per_day"):
		value = _whole(doc.get(key), 1)
		if value is None:
			frappe.throw(frappe._("Lesson counts and daily limits must be positive integers"))
		doc.set(key, value)
	group = frappe.get_doc("Student Group", doc.student_group)
	if group.disabled:
		frappe.throw(frappe._("A disabled Student Group cannot be scheduled"))
	if group.group_based_on == "Course" and group.course != doc.course:
		frappe.throw(frappe._("Course must match the course-based Student Group"))


def validate_availability(doc):
	period = frappe.get_doc("Timetable Period", doc.period)
	if doc.day != period.day:
		frappe.throw(frappe._("Availability day must match its period"))
	if not availability_permission(doc, "write"):
		frappe.throw(frappe._("You may only change your own instructor availability"), frappe.PermissionError)


def availability_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if (
		user == "Administrator"
		or "Academic Admin" in frappe.get_roles(user)
		or ptype in ("read", "select", "report", "print")
	):
		return True
	employee = frappe.db.get_value("Instructor", doc.instructor, "employee")
	return bool(employee and frappe.db.get_value("Employee", employee, "user_id") == user)


def validate_run(doc):
	doc.max_backtracks = _whole(doc.max_backtracks, 0)
	if doc.max_backtracks is None:
		frappe.throw(frappe._("Maximum backtracks must be a nonnegative integer"))
	if _run_action.get():
		return
	old = doc.get_doc_before_save()
	protected = ("status", "slots", "conflicts", "generated_on", "generation_error")
	if old:
		if old.status != "Draft" or any(doc.has_value_changed(key) for key in protected):
			frappe.throw(frappe._("Use Generate or Publish to change a timetable run"))
	elif doc.status != "Draft" or doc.slots or doc.conflicts or doc.generated_on or doc.generation_error:
		frappe.throw(frappe._("New timetable runs must be empty drafts"))


def protect_run_deletion(doc):
	if doc.status == "Published":
		frappe.throw(frappe._("Published timetable runs cannot be deleted"))


def protect_course_schedule(doc, method=None):
	"""Protect provenance and published rows even from direct REST writes."""
	if _publishing.get():
		return
	old = doc.get_doc_before_save()
	if doc.get("timetable_run") or (old and old.get("timetable_run")):
		frappe.throw(frappe._("Published timetable schedules can only be replaced by Publish"))


def _inputs(doc):
	term = frappe.get_doc("Academic Term", doc.academic_term)
	groups = frappe.get_all(
		"Student Group",
		filters={"disabled": 0, "academic_year": term.academic_year},
		fields=["name", "academic_term"],
	)
	groups = [g.name for g in groups if not g.academic_term or g.academic_term == term.name]
	requirements = (
		frappe.get_all(
			"Timetable Requirement",
			filters={"student_group": ["in", groups]},
			fields=[
				"name",
				"student_group",
				"course",
				"instructor",
				"lessons_per_week",
				"max_per_day",
				"room",
			],
			order_by="name",
		)
		if groups
		else []
	)
	periods = frappe.get_all("Timetable Period", fields=["name", "day", "start_time", "end_time", "is_break"])
	availability = frappe.get_all("Timetable Availability", fields=["instructor", "day", "period", "type"])
	rooms = frappe.get_all("Room", pluck="name", order_by="name")
	return requirements, periods, availability, rooms


def _generate(run: str):
	from frappe.utils import now_datetime

	_guard(run)
	doc = frappe.get_doc("Timetable Run", run, for_update=True)
	if doc.status == "Published":
		frappe.throw(frappe._("Published runs cannot be regenerated; create a new run"))
	frappe.db.savepoint("timetable_generation")
	try:
		inputs = _inputs(doc)
		if not inputs[0]:
			frappe.throw(frappe._("No timetable requirements exist for this term's student groups"))
		result = solve(*inputs, max_backtracks=doc.max_backtracks)
		doc.set("slots", result["slots"])
		for conflict in result["conflicts"]:
			conflict["reason"] = frappe._(
				"No feasible period/room within availability, resource and daily limits (search bound {0})."
			).format(doc.max_backtracks)
		doc.set("conflicts", result["conflicts"])
		doc.status = "Generated"
		doc.generated_on = now_datetime()
		doc.generation_error = None
		with _action(_run_action):
			doc.save()
	except Exception:
		frappe.db.rollback(save_point="timetable_generation")
		frappe.log_error(title=frappe._("Timetable generation failed"))
		doc = frappe.get_doc("Timetable Run", run, for_update=True)
		doc.status = "Failed"
		doc.generation_error = frappe._(
			"Generation failed. Ask an Academic Admin to review the Error Log and regenerate."
		)
		with _action(_run_action):
			doc.save()
		return {"ok": False, "name": run, "message": doc.generation_error}
	return {"ok": True, "name": run, "message": frappe._("Timetable generated")}


def _has_schedule_links(name):
	"""Conservative replacement: even cancelled or framework-ignored links block deletion."""
	from frappe.model.dynamic_links import get_dynamic_link_map
	from frappe.model.rename_doc import get_link_fields

	for field in get_link_fields("Course Schedule"):
		if field["issingle"]:
			if frappe.db.get_single_value(field["parent"], field["fieldname"]) == name:
				return True
		elif frappe.db.exists(field["parent"], {field["fieldname"]: name}):
			return True
	for field in get_dynamic_link_map().get("Course Schedule", []):
		if frappe.get_meta(field.parent).issingle:
			values = frappe.db.get_singles_dict(field.parent)
			if values.get(field.options) == "Course Schedule" and values.get(field.fieldname) == name:
				return True
		elif frappe.db.exists(field.parent, {field.options: "Course Schedule", field.fieldname: name}):
			return True
	return False


def _validate_slots(doc):
	"""Reject stale generated plans rather than publishing changed requirements."""
	requirements, periods, availability, rooms = _inputs(doc)
	requirements = {row.name: row for row in requirements}
	periods = {row.name: row for row in periods}
	counts, daily = {}, {}
	placed = []
	for slot in doc.slots:
		req, period = requirements.get(slot.requirement), periods.get(slot.period)
		stale = not req or not period
		if not stale:
			stale = (
				any(slot.get(key) != req.get(key) for key in ("instructor", "student_group", "course"))
				or (req.room and req.room != slot.room)
				or slot.room not in rooms
				or slot.day != period.day
				or seconds(slot.start_time) != seconds(period.start_time)
				or seconds(slot.end_time) != seconds(period.end_time)
				or period.is_break
				or any(p.is_break and overlaps(slot.as_dict(), p) for p in periods.values())
				or any(
					a.instructor == slot.instructor and overlaps(slot.as_dict(), periods[a.period])
					for a in availability
				)
			)
		if stale:
			frappe.throw(frappe._("Scheduling inputs changed; regenerate this run before publishing"))
		counts[slot.requirement] = counts.get(slot.requirement, 0) + 1
		key = (slot.requirement, slot.day)
		daily[key] = daily.get(key, 0) + 1
		if daily[key] > req.max_per_day or any(
			overlaps(slot.as_dict(), other.as_dict())
			and any(
				slot.get(resource) == other.get(resource)
				for resource in ("instructor", "room", "student_group")
			)
			for other in placed
		):
			frappe.throw(frappe._("Timetable constraints changed; regenerate before publishing"))
		placed.append(slot)
	if any(counts.get(name, 0) != req.lessons_per_week for name, req in requirements.items()):
		frappe.throw(frappe._("Lesson requirements changed; regenerate before publishing"))


def _publish(run: str):
	from frappe.utils import getdate

	_guard(run)
	term_name = frappe.db.get_value("Timetable Run", run, "academic_term")
	# Serialize every run for this term before locking individual runs/schedules.
	term = frappe.get_doc("Academic Term", term_name, for_update=True)
	doc = frappe.get_doc("Timetable Run", run, for_update=True)
	if doc.academic_term != term.name:
		frappe.throw(frappe._("The run's term changed; reload and try again"))
	if doc.status == "Published":
		return {"ok": True, "name": run, "message": frappe._("Timetable already published")}
	if doc.status != "Generated":
		frappe.throw(frappe._("Generate the timetable before publishing"))
	if doc.conflicts:
		frappe.throw(frappe._("Resolve all unplaced lessons before publishing"))
	if not doc.slots:
		frappe.throw(frappe._("An empty timetable cannot be published"))
	if not term.term_start_date or not term.term_end_date:
		frappe.throw(frappe._("Academic Term requires a valid start and end date"))
	start, end = getdate(term.term_start_date), getdate(term.term_end_date)
	if start > end:
		frappe.throw(frappe._("Academic Term requires a valid start and end date"))
	for doctype, key in (("Instructor", "instructor"), ("Room", "room"), ("Student Group", "student_group")):
		for name in sorted({slot.get(key) for slot in doc.slots if slot.get(key)}):
			frappe.get_doc(doctype, name, for_update=True)
	_validate_slots(doc)
	dates = {day: [] for day in DAYS}
	date = start
	while date <= end:
		dates[DAYS[date.weekday()]].append(date)
		date += timedelta(days=1)
	if any(not dates[slot.day] for slot in doc.slots):
		frappe.throw(
			frappe._("The term has no date for one or more weekly slots; regenerate with matching periods")
		)
	prior = frappe.get_all(
		"Timetable Run",
		filters={"academic_term": term.name, "status": "Published", "name": ["!=", run]},
		pluck="name",
	)
	names = (
		frappe.get_all(
			"Course Schedule", filters={"timetable_run": ["in", prior]}, pluck="name", order_by="name"
		)
		if prior
		else []
	)
	blocked = []
	for name in names:
		frappe.get_doc("Course Schedule", name, for_update=True)
		if _has_schedule_links(name):
			blocked.append(name)
	if blocked:
		frappe.throw(
			frappe._("Cannot replace linked Course Schedules: {0}").format(", ".join(blocked)),
			frappe.LinkExistsError,
		)
	frappe.has_permission("Course Schedule", "create", throw=True)
	for name in names:
		frappe.has_permission("Course Schedule", "delete", doc=name, throw=True)
	frappe.db.savepoint("timetable_publish")
	try:
		with _action(_publishing):
			for name in names:
				frappe.delete_doc("Course Schedule", name)
			for slot in doc.slots:
				for day in dates[slot.day]:
					schedule = frappe.get_doc(
						{
							"doctype": "Course Schedule",
							"naming_series": "EDU-CSH-.YYYY.-",
							"student_group": slot.student_group,
							"course": slot.course,
							"instructor": slot.instructor,
							"room": slot.room,
							"schedule_date": day,
							"from_time": slot.start_time,
							"to_time": slot.end_time,
							"timetable_run": run,
						}
					).insert()
					if schedule.course != slot.course:
						frappe.throw(frappe._("Student Group course changed; regenerate before publishing"))
		with _action(_run_action):
			doc.status = "Published"
			doc.save()
	except Exception:
		frappe.db.rollback(save_point="timetable_publish")
		raise
	return {"ok": True, "name": run, "message": frappe._("Timetable published")}


@frappe.whitelist(methods=["POST"])
def generate(run: str) -> dict:
	_guard(run)
	doc = frappe.get_doc("Timetable Run", run)
	if doc.status == "Published":
		frappe.throw(frappe._("Published runs cannot be regenerated; create a new run"))
	frappe.enqueue(
		"frappe_education_kenya.timetable._generate",
		run=run,
		queue="long",
		timeout=1500,
		enqueue_after_commit=True,
		job_id=f"timetable::{run}",
		deduplicate=True,
	)
	return {"ok": True, "name": run, "message": frappe._("Timetable generation queued")}


@frappe.whitelist(methods=["POST"])
def publish(run: str) -> dict:
	_guard(run)
	return _publish(run)
