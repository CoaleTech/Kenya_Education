"""Retire the Kenya navigation this app used to inject at runtime.

Every migrate used to write Kenya's cards, charts, shortcuts and links into the
shared "Education" workspace, the Kenya links into the archived `Workspace
Sidebar` (which the v16.55 Desk no longer reads), and to create the analytics as
site documents. All of it now ships as standard files: a Workspace, Sidebar,
Dock, Number Cards and Dashboard Charts.

This runs before model sync so the injected copies are gone when the standard
cards and charts of the same name are imported.
"""

import json

import frappe

CARDS = [
	"Total Students",
	"Instructors",
	"Program Enrollments",
	"Student Applicants",
	"CBC Transport Routes",
	"CBC Meal Programmes",
	"MoE Return Submissions",
	"Student Transitions",
]
CHARTS = [
	"Enrollments by Program",
	"Applicants by Status",
	"CBC Students by Level",
	"CBC Students by Boarder Status",
	"CBC Assessment Performance Levels",
]
SHORTCUTS = [
	# current labels
	"CBC Levels",
	"Learning Areas",
	"Assessments",
	"Results (CBC)",
	"Transitions",
	"Transport Routes",
	"Meals",
	"MoE Submissions",
	# labels from earlier releases
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
]
CARD_BREAKS = [
	"Kenya CBC Curriculum",
	"Kenya Assessment",
	"Kenya Student Lifecycle",
	"Kenya Transport",
	"Kenya Meals & Feeding",
	"Kenya MoE Compliance",
	"Kenya Geography",
	"Kenya Settings",
]
HEADER_MARKERS = ("Analytics", "Kenya CBC", "Kenya Shortcuts", "Kenya Masters")
LEGACY_WORKSPACE = "Kenya Education"


def execute():
	_clean_education_workspace()

	for doctype, names in (("Number Card", CARDS), ("Dashboard Chart", CHARTS)):
		for name in names:
			# is_standard rows are the shipped files; only the runtime copies go
			if frappe.db.get_value(doctype, name, "is_standard") == 0:
				frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)

	for doctype in ("Workspace", "Workspace Sidebar", "Desktop Icon"):
		if frappe.db.exists("DocType", doctype) and frappe.db.exists(doctype, LEGACY_WORKSPACE):
			frappe.delete_doc(doctype, LEGACY_WORKSPACE, force=True, ignore_permissions=True)


def _clean_education_workspace():
	if not frappe.db.exists("Workspace", "Education"):
		return

	# Direct writes: Education is the host app's workspace, and a standard one cannot be saved
	# from a site. The rows removed here were never part of its shipped file.
	content = json.loads(frappe.db.get_value("Workspace", "Education", "content") or "[]")
	frappe.db.set_value(
		"Workspace", "Education", "content", json.dumps(_strip_owned_blocks(content)), update_modified=False
	)

	parent = {"parent": "Education", "parenttype": "Workspace"}
	frappe.db.delete("Workspace Number Card", {**parent, "number_card_name": ("in", CARDS)})
	frappe.db.delete("Workspace Chart", {**parent, "chart_name": ("in", CHARTS)})
	frappe.db.delete("Workspace Shortcut", {**parent, "label": ("in", SHORTCUTS)})

	# The Kenya cards were always appended last: drop every link row from the first Kenya card break.
	first = frappe.db.get_value(
		"Workspace Link",
		{**parent, "type": "Card Break", "label": ("in", CARD_BREAKS)},
		"idx",
		order_by="idx asc",
	)
	if first:
		frappe.db.delete("Workspace Link", {**parent, "idx": (">=", first)})


def _strip_owned_blocks(blocks):
	kept = []
	for block in blocks:
		data = block.get("data") or {}
		kind = block.get("type")
		owned = (
			(kind == "header" and any(m in (data.get("text") or "") for m in HEADER_MARKERS))
			or (kind == "number_card" and data.get("number_card_name") in CARDS)
			or (kind == "chart" and data.get("chart_name") in CHARTS)
			or (kind == "shortcut" and data.get("shortcut_name") in SHORTCUTS)
			or (kind == "card" and data.get("card_name") in CARD_BREAKS)
		)
		if owned:
			# an earlier release put a spacer in front of its header
			if kept and kept[-1].get("type") == "spacer":
				kept.pop()
			continue
		kept.append(block)
	return kept
