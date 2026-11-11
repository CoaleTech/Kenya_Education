"""Topic CBC links: the strand sits at the Topic's level, the sub-strand under its strand."""

import frappe
from frappe.tests.utils import FrappeTestCase


def _insert(**values):
	return frappe.get_doc(values).insert(ignore_permissions=True).name


def make_curriculum():
	"""Two levels, each with one strand and one sub-strand, under one learning area."""
	levels = [
		_insert(
			doctype="CBC Level",
			level_code=f"TC-L{i}",
			level_name=f"Topic Curriculum Level {i}",
			education_sector="Primary",
			years_of_study=1,
			sequence_order=900 + i,
			moef_level_code=f"TC{i}",
		)
		for i in (1, 2)
	]
	area = _insert(
		doctype="CBC Learning Area",
		learning_area_code="TC-LA",
		learning_area_name="Topic Curriculum Area",
		learning_area_category="Sciences",
		applicable_levels=[{"cbc_level": level} for level in levels],
	)
	strands = [
		_insert(
			doctype="CBC Strand",
			strand_code=f"TC-S{i}",
			strand_name=f"Topic Curriculum Strand {i}",
			learning_area=area,
			cbc_level=level,
		)
		for i, level in enumerate(levels, 1)
	]
	sub_strands = [
		_insert(
			doctype="CBC Sub Strand",
			sub_strand_code=f"TC-SS{i}",
			sub_strand_name=f"Topic Curriculum Sub Strand {i}",
			strand=strand,
		)
		for i, strand in enumerate(strands, 1)
	]
	return frappe._dict(levels=levels, strands=strands, sub_strands=sub_strands)


def make_topic(level, strand, sub_strand=None):
	return frappe.get_doc(
		{
			"doctype": "Topic",
			"topic_name": "Topic Curriculum Plants",
			"cbc_level": level,
			"cbc_strand": strand,
			"cbc_sub_strand": sub_strand,
		}
	).insert(ignore_permissions=True)


class TestTopicCurriculum(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.cbc = make_curriculum()

	def test_matching_links_are_saved(self):
		level, strand, sub_strand = (self.cbc[k][0] for k in ("levels", "strands", "sub_strands"))
		topic = make_topic(level, strand, sub_strand)
		self.assertEqual(
			frappe.db.get_value("Topic", topic.name, ["cbc_level", "cbc_strand", "cbc_sub_strand"]),
			(level, strand, sub_strand),
		)

	def test_strand_from_another_level_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			make_topic(self.cbc.levels[1], self.cbc.strands[0])

	def test_strand_without_level_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			make_topic(None, self.cbc.strands[0])

	def test_sub_strand_of_another_strand_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			make_topic(self.cbc.levels[0], self.cbc.strands[0], self.cbc.sub_strands[1])

	def test_sub_strand_without_strand_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			make_topic(None, None, self.cbc.sub_strands[0])

	def test_topic_without_curriculum_links_is_unaffected(self):
		self.assertTrue(make_topic(None, None).name)
