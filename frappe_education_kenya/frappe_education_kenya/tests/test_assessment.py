"""Tests for CBC assessment Performance-Level mapping."""

import frappe
from frappe.tests.utils import FrappeTestCase

from frappe_education_kenya.frappe_education_kenya.assessment import (
	PERFORMANCE_LEVEL_LABELS,
	map_assessment_to_performance_level,
	resolve_performance_level,
)


class FakeDoc(dict):
	"""Minimal doc stand-in that supports both dict.get() and attribute assignment.

	The assessment hook reads values via `doc.get(...)` and writes the mapped
	performance level back via `doc.cbc_performance_level = ...`, so the fake
	must expose both access patterns.
	"""

	def get(self, k, default=None):
		return dict.get(self, k, default)

	def __setattr__(self, name, value):
		if name.startswith("__") and name.endswith("__"):
			raise AttributeError(name)
		self[name] = value

	def __getattr__(self, name):
		if name.startswith("__") and name.endswith("__"):
			raise AttributeError(name)
		return self.get(name)


class TestAssessmentPerformanceLevel(FrappeTestCase):
	"""Cover the CBC Performance-Level mapping behaviour."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		field = frappe.get_meta("Assessment Result").get_field("cbc_performance_level")
		cls.valid_options = [opt.strip() for opt in (field.options or "").split("\n") if opt.strip()]
		cls.valid_labels = set(PERFORMANCE_LEVEL_LABELS.values())

	def tearDown(self):
		frappe.db.rollback()

	def test_resolve_performance_level_honours_seeded_scale_thresholds(self):
		cases = [
			(100, "PL1"),
			(80, "PL1"),
			(79.9, "PL2"),
			(65, "PL2"),
			(64.9, "PL3"),
			(50, "PL3"),
			(49, "PL4"),
			(0, "PL4"),
			(-1, None),
		]
		for percentage, expected in cases:
			with self.subTest(percentage=percentage):
				result = resolve_performance_level(percentage)
				self.assertEqual(result, expected)

	def test_resolve_performance_level_returns_none_for_missing_scale(self):
		result = resolve_performance_level(50, grading_scale="Nonexistent Scale")
		self.assertIsNone(result)

	def test_map_assessment_sets_labelled_performance_level_for_each_band(self):
		cases = [
			# total_score, maximum_score, expected_code, expected_label
			(90, 100, "PL1", "PL1 - Exceeds Expectations"),
			(35, 50, "PL2", "PL2 - Meets Expectations"),
			(25, 50, "PL3", "PL3 - Approaches Expectations"),
			(10, 100, "PL4", "PL4 - Below Expectations"),
		]
		for total, maximum, code, expected in cases:
			with self.subTest(total=total, maximum=maximum):
				doc = FakeDoc(total_score=total, maximum_score=maximum)
				map_assessment_to_performance_level(doc)
				self.assertEqual(doc.get("cbc_performance_level"), expected)
				self.assertEqual(doc.cbc_performance_level, expected)
				self.assertIn(expected, self.valid_options)
				self.assertIn(expected, self.valid_labels)
				self.assertEqual(PERFORMANCE_LEVEL_LABELS.get(code), expected)

	def test_map_assessment_no_op_when_total_score_is_none(self):
		doc = FakeDoc(total_score=None, maximum_score=100)
		map_assessment_to_performance_level(doc)
		self.assertIsNone(doc.get("cbc_performance_level"))

	def test_map_assessment_no_op_when_maximum_score_is_zero(self):
		doc = FakeDoc(total_score=50, maximum_score=0)
		map_assessment_to_performance_level(doc)
		self.assertIsNone(doc.get("cbc_performance_level"))

	def test_map_assessment_no_op_when_maximum_score_is_none(self):
		doc = FakeDoc(total_score=50, maximum_score=None)
		map_assessment_to_performance_level(doc)
		self.assertIsNone(doc.get("cbc_performance_level"))

	def test_map_assessment_no_op_when_total_score_is_non_numeric(self):
		doc = FakeDoc(total_score="abc", maximum_score=100)
		map_assessment_to_performance_level(doc)
		self.assertIsNone(doc.get("cbc_performance_level"))
