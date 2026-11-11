"""The Kenya sidebar layer: it must keep naming every Education row, and place Kenya's student
links inside Education's Student Management section."""

import json

import frappe
from frappe.desk.doctype.custom_sidebar.custom_sidebar import resolve_arrangement
from frappe.desk.doctype.sidebar.sidebar import item_key
from frappe.tests.utils import FrappeTestCase

STUDENT_LINKS = (
	"Student Transition",
	"Student Pathway Choice",
	"CBC Pathway",
	"CBC Track",
	"CBC Subject Combination",
	"CBC Student Settings",
)


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
