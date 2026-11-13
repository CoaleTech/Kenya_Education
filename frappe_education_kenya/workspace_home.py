"""Kenya's part of the Education Home page.

Education's own workspace is not a standard (file-owned) one, so Desk gives it no site layer.
Kenya's analytics, shortcuts and link cards are therefore folded into it here, on install and on
every migrate, from `home.json` (a Workspace-shaped file: the widget rows, plus the content
blocks to put above (`top`) and below (`bottom`) Education's own).

Idempotent: this app's rows are found by label and its blocks by id, removed, then added again,
so a re-run, or Education re-syncing its workspace file, never leaves a duplicate.
"""

import json

import frappe

HOME = "Education"
TABLES = ("number_cards", "charts", "shortcuts", "links")


def load():
	with open(frappe.get_app_path("frappe_education_kenya", "home.json")) as f:
		return json.load(f)


def merge_home():
	if not frappe.db.exists("Workspace", HOME):
		return

	ws = frappe.get_doc("Workspace", HOME)
	ws.type = ws.type or "Workspace"  # Education's record can predate the mandatory `type` field
	fold_into(ws, load())
	ws.save(ignore_permissions=True)


def fold_into(ws, home):
	"""Replace this app's rows and blocks in the Workspace `ws` with the ones in `home`."""
	for table in ("number_cards", "charts", "shortcuts"):
		own = {row["label"] for row in home[table]}
		ws.set(table, [row for row in ws.get(table) if row.label not in own])

	# a card is a Card Break row plus the Link rows under it
	own = {row["label"] for row in home["links"] if row["type"] == "Card Break"}
	kept, skipping = [], False
	for row in ws.links:
		if row.type == "Card Break":
			skipping = row.label in own
		if not skipping:
			kept.append(row)
	ws.set("links", kept)

	for table in TABLES:
		for row in home[table]:
			ws.append(table, row)
		# rows kept from before can leave gaps in idx, and Desk draws cards in idx order
		for idx, row in enumerate(ws.get(table), 1):
			row.idx = idx

	ids = {block["id"] for block in home["top"] + home["bottom"]}
	base = [block for block in json.loads(ws.content or "[]") if block["id"] not in ids]
	ws.content = json.dumps(home["top"] + base + home["bottom"])
