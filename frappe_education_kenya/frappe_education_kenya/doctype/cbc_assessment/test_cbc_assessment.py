"""Tests for CBC Assessment score-to-performance-level mapping."""

import frappe
from frappe.tests.utils import FrappeTestCase

from frappe_education_kenya.frappe_education_kenya.doctype.cbc_assessment.cbc_assessment import (
	_score_to_performance_level,
	map_assessment_to_performance_level,
)


class FakeDoc(dict):
	"""Minimal attribute+dict hybrid to exercise doc-hook functions without a real DocType."""

	def get(self, k, default=None):
		return dict.get(self, k, default)

	def __getattr__(self, k):
		try:
			return self[k]
		except KeyError:
			raise AttributeError(k)

	def __setattr__(self, k, v):
		self[k] = v


class TestCBCAssessmentBands(FrappeTestCase):
	def test_pl1_band(self):
		self.assertEqual(_score_to_performance_level(80), "PL1")
		self.assertEqual(_score_to_performance_level(92), "PL1")
		self.assertEqual(_score_to_performance_level(100), "PL1")

	def test_pl2_band(self):
		self.assertEqual(_score_to_performance_level(65), "PL2")
		self.assertEqual(_score_to_performance_level(70), "PL2")
		self.assertEqual(_score_to_performance_level(79.999), "PL2")

	def test_pl3_band(self):
		self.assertEqual(_score_to_performance_level(50), "PL3")
		self.assertEqual(_score_to_performance_level(55), "PL3")
		self.assertEqual(_score_to_performance_level(64.999), "PL3")

	def test_pl4_band(self):
		self.assertEqual(_score_to_performance_level(0), "PL4")
		self.assertEqual(_score_to_performance_level(30), "PL4")
		self.assertEqual(_score_to_performance_level(49.999), "PL4")

	def test_boundary_just_below_pl1(self):
		# 79.9999... is technically < 80, should fall to PL2 band top (79.999)
		self.assertEqual(_score_to_performance_level(79.9995), "PL2")

	def test_custom_criteria_override(self):
		criteria = [
			{"minimum_score": 90, "maximum_score": 100, "performance_level": "PL1"},
			{"minimum_score": 0, "maximum_score": 89.999, "performance_level": "PL4"},
		]
		self.assertEqual(_score_to_performance_level(95, criteria), "PL1")
		self.assertEqual(_score_to_performance_level(85, criteria), "PL4")
		# Without custom criteria, 85 would have been PL1 (>= 80)
		self.assertEqual(_score_to_performance_level(85), "PL1")

	def test_incomplete_custom_criteria_falls_back_to_default(self):
		# Rows missing minimum_score/maximum_score/performance_level are skipped;
		# if none are usable, default bands apply.
		criteria = [{"minimum_score": None, "maximum_score": None, "performance_level": None}]
		self.assertEqual(_score_to_performance_level(92, criteria), "PL1")

	def test_out_of_range_score_returns_none(self):
		# No band covers e.g. -5 or 150; function should not raise.
		self.assertIsNone(_score_to_performance_level(-5))
		self.assertIsNone(_score_to_performance_level(150))


class TestMapAssessmentToPerformanceLevel(FrappeTestCase):
	def test_computes_percentage_and_sets_level(self):
		doc = FakeDoc(total_score=92, maximum_score=100, assessment_plan=None, assessment_group=None)
		map_assessment_to_performance_level(doc)
		self.assertEqual(doc.get("cbc_performance_level"), "PL1")

	def test_fractional_scores(self):
		doc = FakeDoc(total_score=35, maximum_score=50, assessment_plan=None, assessment_group=None)
		map_assessment_to_performance_level(doc)
		self.assertEqual(doc.get("cbc_performance_level"), "PL2")

	def test_missing_total_score_noop(self):
		doc = FakeDoc(total_score=None, maximum_score=100, assessment_plan=None, assessment_group=None)
		map_assessment_to_performance_level(doc)
		self.assertIsNone(doc.get("cbc_performance_level"))

	def test_zero_maximum_score_does_not_raise(self):
		doc = FakeDoc(total_score=5, maximum_score=0, assessment_plan=None, assessment_group=None)
		# Should not raise ZeroDivisionError
		map_assessment_to_performance_level(doc)
		self.assertIsNone(doc.get("cbc_performance_level"))

	def test_non_numeric_scores_do_not_raise(self):
		doc = FakeDoc(total_score="abc", maximum_score=100, assessment_plan=None, assessment_group=None)
		map_assessment_to_performance_level(doc)
		self.assertIsNone(doc.get("cbc_performance_level"))

	def tearDown(self):
		frappe.db.rollback()
