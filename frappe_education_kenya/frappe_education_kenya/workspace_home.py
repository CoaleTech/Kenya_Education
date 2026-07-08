"""Unified desk home for Frappe Education + Kenya.

Frappe Education is the primary app; Kenya localises it. Rather than shipping a
second workspace home, this module folds the Kenya CBC content AND analytics
(number cards + dashboard charts) into the single base "Education" workspace,
then retires the standalone "Kenya Education" workspace.

All of this lives in the Kenya app and runs from install / after_migrate.
Layout: the analytics block (number cards + charts) is PREPENDED so dashboards
sit at the top of the home, base Education content follows, and the Kenya
navigation block is appended last. Idempotent: every injected block is
identified by its payload (widget names / header markers) and stripped before
re-injection, so it survives the base workspace being re-synced from its JSON
on every migrate and cleans up older layout revisions.
"""

import json

import frappe

EDUCATION_WORKSPACE = "Education"
KENYA_WORKSPACE = "Kenya Education"

# Header of the Kenya navigation block appended after the base content.
KENYA_HEADER_TEXT = '<span class="h4"><b>Kenya CBC &amp; Compliance</b></span>'

# ── Analytics ────────────────────────────────────────────────────────────────
# The "School Analytics" block covers BOTH apps: base Frappe Education metrics
# (students, staff, enrolment, admissions) and the Kenya localisation metrics
# (transport, meals, MoE compliance, transitions). Base Education ships no
# desk analytics of its own, so these are created here (owned by this app).
#
# Number cards (Count of a DocType). name == label (Number Card.autoname).
# 8 cards @ col 3 => two clean rows: base Education row, then Kenya row.
HOME_NUMBER_CARDS = [
	# Base Frappe Education
	{"label": "Total Students", "document_type": "Student", "color": "#449CF0"},
	{"label": "Instructors", "document_type": "Instructor", "color": "#7C7C7C"},
	{
		"label": "Program Enrollments",
		"document_type": "Program Enrollment",
		"color": "#29CD42",
		# submittable: count only submitted enrolments
		"filters_json": '[["Program Enrollment","docstatus","=",1]]',
	},
	{"label": "Student Applicants", "document_type": "Student Applicant", "color": "#EC864B"},
	# Kenya localisation
	{"label": "CBC Transport Routes", "document_type": "Transport Route", "color": "#ECAD4B"},
	{"label": "CBC Meal Programmes", "document_type": "Meal Programme", "color": "#29CD42"},
	{"label": "MoE Return Submissions", "document_type": "MoE Return Submission", "color": "#CB2929"},
	{"label": "Student Transitions", "document_type": "Student Transition", "color": "#B554F0"},
]

# Group-By dashboard charts. name == chart_name. `col` is the workspace grid
# width (12 = full row). Layout: base row (6+6), Kenya row (6+6), full-width
# assessment bar to close the block on a balanced row.
HOME_CHARTS = [
	# Base Frappe Education
	{
		"chart_name": "Enrollments by Program",
		"document_type": "Program Enrollment",
		"group_by_based_on": "program",
		"type": "Donut",
		"color": "#29CD42",
		"col": 6,
		"filters_json": '[["Program Enrollment","docstatus","=",1]]',
	},
	{
		"chart_name": "Applicants by Status",
		"document_type": "Student Applicant",
		"group_by_based_on": "application_status",
		"type": "Donut",
		"color": "#EC864B",
		"col": 6,
	},
	# Kenya localisation
	{
		"chart_name": "CBC Students by Level",
		"document_type": "Student",
		"group_by_based_on": "kenya_cbc_level",
		"type": "Donut",
		"color": "#449CF0",
		"col": 6,
	},
	{
		"chart_name": "CBC Students by Boarder Status",
		"document_type": "Student",
		"group_by_based_on": "kenya_boarder_status",
		"type": "Donut",
		"color": "#29CD42",
		"col": 6,
	},
	{
		"chart_name": "CBC Assessment Performance Levels",
		"document_type": "Assessment Result",
		"group_by_based_on": "cbc_performance_level",
		"type": "Bar",
		"color": "#ECAD4B",
		"col": 12,
	},
]

# ── Navigation content ───────────────────────────────────────────────────────
# Labels are kept short enough for a col-3 shortcut chip (~16 chars) so two
# related chips never truncate to identical text. Exactly 8 => two clean rows.
KENYA_SHORTCUTS = [
	("CBC Levels", "CBC Level", "Green"),
	("Learning Areas", "CBC Learning Area", "Blue"),
	("Assessments", "Assessment Plan", "Orange"),
	("Results (CBC)", "Assessment Result", "Purple"),
	("Transitions", "Student Transition", "Grey"),
	("Transport Routes", "Transport Route", "Yellow"),
	("Meals", "Meal Programme", "Green"),
	("MoE Submissions", "MoE Return Submission", "Red"),
]

# Labels used by earlier releases; stripped alongside current ones so upgrades
# never leave orphan shortcut rows behind.
_LEGACY_SHORTCUT_LABELS = {
	"CBC Assessments",
	"CBC Assessment Plans",
	"CBC Assessment Results",
	"Assessment Results",
	"Student Transitions",
	"Transport Vehicles",
	"Meal Programmes",
	"Daily Meal Records",
	"MoE Return Templates",
	"Education Kenya Settings",
}

# (card label, [(link label, doctype), ...]). Labels are "Kenya "-prefixed so
# they never collide with base Education card/link labels.
KENYA_CARDS = [
	(
		"Kenya CBC Curriculum",
		[
			("CBC Level", "CBC Level"),
			("CBC Learning Area", "CBC Learning Area"),
			("CBC Strand", "CBC Strand"),
			("CBC Sub Strand", "CBC Sub Strand"),
			("CBC Learning Outcome", "CBC Learning Outcome"),
		],
	),
	(
		"Kenya Assessment",
		[
			("CBC Assessment Plan", "Assessment Plan"),
			("CBC Assessment Result", "Assessment Result"),
		],
	),
	(
		"Kenya Student Lifecycle",
		[
			("Student Transition", "Student Transition"),
			("CBC Student Settings", "CBC Student Settings"),
		],
	),
	(
		"Kenya Transport",
		[
			("Transport Route", "Transport Route"),
			("Transport Vehicle", "Transport Vehicle"),
			("Transport Subscription", "Transport Subscription"),
		],
	),
	(
		"Kenya Meals & Feeding",
		[
			("Meal Programme", "Meal Programme"),
			("Daily Meal Record", "Daily Meal Record"),
			("Student Meal Subscription", "Student Meal Subscription"),
		],
	),
	(
		"Kenya MoE Compliance",
		[
			("MoE Return Template", "MoE Return Template"),
			("MoE Return Submission", "MoE Return Submission"),
		],
	),
	(
		"Kenya Geography",
		[
			("Kenya County", "Kenya County"),
			("Kenya Sub County", "Kenya Sub County"),
		],
	),
	(
		"Kenya Settings",
		[
			("Education Kenya Settings", "Education Kenya Settings"),
			("CBC Fee Settings", "CBC Fee Settings"),
		],
	),
]

_CHART_NAMES = {c["chart_name"] for c in HOME_CHARTS}
_CARD_NAMES = {c["label"] for c in HOME_NUMBER_CARDS}
_CARD_BREAK_LABELS = {label for label, _links in KENYA_CARDS}


def _hid():
	return frappe.generate_hash(length=10)


def seed_cbc_analytics():
	"""Create the school analytics widgets for both apps (idempotent, public)."""
	for card in HOME_NUMBER_CARDS:
		if frappe.db.exists("Number Card", card["label"]):
			continue
		doc = frappe.new_doc("Number Card")
		doc.update(
			{
				"label": card["label"],
				"type": "Document Type",
				"document_type": card["document_type"],
				"function": "Count",
				"is_public": 1,
				"filters_json": card.get("filters_json", "[]"),
				"color": card["color"],
			}
		)
		doc.insert(ignore_permissions=True)

	for chart in HOME_CHARTS:
		if frappe.db.exists("Dashboard Chart", chart["chart_name"]):
			continue
		doc = frappe.new_doc("Dashboard Chart")
		doc.update(
			{
				"chart_name": chart["chart_name"],
				"chart_type": "Group By",
				"document_type": chart["document_type"],
				"group_by_type": "Count",
				"group_by_based_on": chart["group_by_based_on"],
				"number_of_groups": 0,
				"type": chart["type"],
				"is_public": 1,
				"timeseries": 0,
				"filters_json": chart.get("filters_json", "[]"),
				"color": chart["color"],
			}
		)
		doc.insert(ignore_permissions=True)


def merge_kenya_home_into_education():
	"""Fold Kenya analytics + navigation into the single Education workspace."""
	if not frappe.db.exists("Workspace", EDUCATION_WORKSPACE):
		return

	seed_cbc_analytics()

	ws = frappe.get_doc("Workspace", EDUCATION_WORKSPACE)

	_strip_previous_kenya_block(ws)
	_append_kenya_child_rows(ws)
	ws.content = _compose_content(ws.content)

	# The base Education workspace predates the reqd `type` field, so its DB
	# record has it empty; set the default before saving to pass validation.
	if not ws.get("type"):
		ws.type = "Workspace"

	ws.save(ignore_permissions=True)

	# Retire the now-redundant standalone Kenya workspace so there is one home.
	if frappe.db.exists("Workspace", KENYA_WORKSPACE):
		frappe.delete_doc("Workspace", KENYA_WORKSPACE, ignore_permissions=True, force=True)


def _strip_previous_kenya_block(ws):
	"""Remove any Kenya rows injected by a previous run (keeps base rows)."""
	ws.number_cards = [r for r in ws.number_cards if r.number_card_name not in _CARD_NAMES]
	ws.charts = [r for r in ws.charts if r.chart_name not in _CHART_NAMES]
	kenya_shortcut_labels = {s[0] for s in KENYA_SHORTCUTS} | _LEGACY_SHORTCUT_LABELS
	ws.shortcuts = [r for r in ws.shortcuts if r.label not in kenya_shortcut_labels]

	# Links: the Kenya cards are always appended last, so drop everything from
	# the first Kenya card break onward.
	links = list(ws.links)
	cut = next(
		(i for i, l in enumerate(links) if l.type == "Card Break" and l.label in _CARD_BREAK_LABELS),
		None,
	)
	if cut is not None:
		ws.links = links[:cut]


def _append_kenya_child_rows(ws):
	for card in HOME_NUMBER_CARDS:
		ws.append("number_cards", {"number_card_name": card["label"], "label": card["label"]})
	for chart in HOME_CHARTS:
		ws.append("charts", {"chart_name": chart["chart_name"], "label": chart["chart_name"]})
	for label, link_to, color in KENYA_SHORTCUTS:
		ws.append(
			"shortcuts",
			{
				"type": "DocType",
				"label": label,
				"link_to": link_to,
				"color": color,
			},
		)
	for card_label, card_links in KENYA_CARDS:
		ws.append(
			"links",
			{
				"type": "Card Break",
				"label": card_label,
				"link_type": "DocType",
				"link_count": len(card_links),
				"hidden": 0,
				"onboard": 0,
				"is_query_report": 0,
			},
		)
		for link_label, doctype in card_links:
			ws.append(
				"links",
				{
					"type": "Link",
					"label": link_label,
					"link_to": doctype,
					"link_type": "DocType",
					"link_count": 0,
					"hidden": 0,
					"onboard": 0,
					"is_query_report": 0,
				},
			)


def _header(text, col=12):
	return {"id": _hid(), "type": "header", "data": {"text": text, "col": col}}


# Header markers identifying blocks owned by this app inside the Education
# workspace content (matched by substring). Covers current and legacy layouts.
_OWNED_HEADER_MARKERS = ("Analytics", "Kenya CBC", "Kenya Shortcuts", "Kenya Masters")


def _strip_owned_blocks(blocks):
	"""Remove every content block this app injected on a previous run.

	Blocks are identified by their payload (widget names / header markers), not
	by position, so this cleans up both the legacy bottom-only layout and the
	current top+bottom layout. A spacer immediately preceding an owned block is
	treated as owned too (legacy runs injected one before the Kenya header).
	"""
	shortcut_labels = {s[0] for s in KENYA_SHORTCUTS} | _LEGACY_SHORTCUT_LABELS
	kept = []
	for block in blocks:
		block_type = block.get("type")
		data = block.get("data") or {}
		owned = (
			(
				block_type == "header"
				and any(marker in (data.get("text") or "") for marker in _OWNED_HEADER_MARKERS)
			)
			or (block_type == "number_card" and data.get("number_card_name") in _CARD_NAMES)
			or (block_type == "chart" and data.get("chart_name") in _CHART_NAMES)
			or (block_type == "shortcut" and data.get("shortcut_name") in shortcut_labels)
			or (block_type == "card" and data.get("card_name") in _CARD_BREAK_LABELS)
		)
		if owned:
			if kept and kept[-1].get("type") == "spacer":
				kept.pop()
			continue
		kept.append(block)
	return kept


def _compose_content(content):
	"""Compose the unified home: analytics on top, base content, Kenya nav last."""
	base = _strip_owned_blocks(json.loads(content or "[]"))

	top = [_header('<span class="h4"><b>School Analytics</b></span>')]
	for card in HOME_NUMBER_CARDS:
		top.append(
			{"id": _hid(), "type": "number_card", "data": {"number_card_name": card["label"], "col": 3}}
		)
	for chart in HOME_CHARTS:
		top.append(
			{"id": _hid(), "type": "chart", "data": {"chart_name": chart["chart_name"], "col": chart["col"]}}
		)

	bottom = [_header(KENYA_HEADER_TEXT)]
	bottom.append(_header('<span class="h5"><b>Kenya Shortcuts</b></span>'))
	for label, _link_to, _color in KENYA_SHORTCUTS:
		bottom.append({"id": _hid(), "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})
	bottom.append(_header('<span class="h5"><b>Kenya Masters &amp; Settings</b></span>'))
	for card_label, _links in KENYA_CARDS:
		bottom.append({"id": _hid(), "type": "card", "data": {"card_name": card_label, "col": 4}})

	return json.dumps(top + base + bottom)
