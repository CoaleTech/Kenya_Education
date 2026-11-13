"""The Kenya sidebar layer must keep naming every Education row and place Kenya's student links
inside Education's Student Management section; Kenya's Home content folds into Education's Home."""

import json

import frappe
from frappe.desk.doctype.custom_sidebar.custom_sidebar import resolve_arrangement
from frappe.desk.doctype.sidebar.sidebar import item_key
from frappe.tests.utils import FrappeTestCase

from frappe_education_kenya import workspace_home

STUDENT_LINKS = (
	"Student Transition",
	"Student Pathway Choice",
	"CBC Pathway",
	"CBC Track",
	"CBC Subject Combination",
)

# block type -> (Workspace table, the row field the block's widget name matches)
WIDGETS = {
	"number_card": ("number_cards", "number_card_name"),
	"chart": ("charts", "chart_name"),
	"shortcut": ("shortcuts", "label"),
	"card": ("links", "label"),
}


def _load(app, *path):
	with open(frappe.get_app_path(app, *path)) as f:
		return json.load(f)


class TestKenyaSidebar(FrappeTestCase):
	def setUp(self):
		self.base = _load("education", "workspace_sidebar", "education.json")["items"]
		layer = _load("frappe_education_kenya", "fixtures", "custom_sidebar.json")[0]["sidebar_items"]
		self.layer = [frappe._dict(row) for row in layer]

	def test_layer_names_every_education_row(self):
		# A row the layer does not name falls after every Kenya section, so a new Education item
		# would land at the bottom of the sidebar. Regenerate the fixture when this fails.
		named = {item_key(row) for row in self.layer if not row.added}
		missing = [row["label"] for row in self.base if item_key(row) not in named]
		self.assertEqual(missing, [])

	def test_student_management_holds_education_and_kenya_student_links(self):
		items, _hidden = resolve_arrangement(self.base, [frappe._dict(sidebar_items=self.layer)])

		section, inside = [], False
		for item in items:
			if not item.get("child"):
				inside = item.get("label") == "Student Management"
			elif inside:
				section.append(item["label"])

		self.assertEqual(section[0], "Student")
		self.assertEqual(section[-len(STUDENT_LINKS) :], list(STUDENT_LINKS))
		self.assertNotIn("Student Lifecycle", [item.get("label") for item in items])


class TestKenyaHome(FrappeTestCase):
	"""Kenya's analytics, shortcuts and cards live on Education's own Home workspace."""

	def setUp(self):
		self.base = _load("education", "education", "workspace", "education", "education.json")
		self.home = workspace_home.load()

	def fold(self, times):
		ws = frappe.get_doc(json.loads(json.dumps(self.base)))
		for _i in range(times):
			workspace_home.fold_into(ws, self.home)
		return ws

	def test_fold_is_idempotent_and_keeps_education_rows_and_blocks(self):
		once, twice = self.fold(1), self.fold(2)

		self.assertEqual(once.content, twice.content)
		for table in workspace_home.TABLES:
			self.assertEqual(len(once.get(table)), len(twice.get(table)), table)
			self.assertEqual([r.idx for r in twice.get(table)], list(range(1, len(twice.get(table)) + 1)))

		base_blocks = json.loads(self.base["content"])
		merged = json.loads(twice.content)
		self.assertEqual([b for b in merged if b in base_blocks], base_blocks)
		self.assertEqual(len(merged), len(base_blocks) + len(self.home["top"]) + len(self.home["bottom"]))
		twice.validate_duplicate_widget_labels()

	def test_every_block_has_its_widget(self):
		ws = self.fold(1)
		for block in json.loads(ws.content):
			if block["type"] not in WIDGETS:
				continue
			table, field = WIDGETS[block["type"]]
			name = block["data"][f"{block['type']}_name"]
			rows = ws.get(table)
			if block["type"] == "card":
				rows = [r for r in rows if r.type == "Card Break"]
			self.assertIn(name, [r.get(field) for r in rows], block)
