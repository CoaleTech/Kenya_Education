"""Boundary checks for Kenyan learner identifiers; no database fixtures."""

import unittest

from frappe_education_kenya.learner_ids import normalize_identifiers


class TestLearnerIdentifiers(unittest.TestCase):
	def test_preserves_uli_and_assessment_leading_zeroes(self):
		values = normalize_identifiers({"kenya_kemis_uli": " 00123 ", "kenya_kjsea_assessment_no": " 0097 "})
		self.assertEqual(values["kenya_kemis_uli"], "00123")
		self.assertEqual(values["kenya_kjsea_assessment_no"], "0097")

	def test_score_bounds_and_year(self):
		for score in (0, 500):
			self.assertEqual(normalize_identifiers({"kenya_kjsea_score": score})["kenya_kjsea_score"], score)
		for score in (-1, 501, 1.5, "nan", "inf"):
			with self.subTest(score=score), self.assertRaises(ValueError):
				normalize_identifiers({"kenya_kjsea_score": score})
		for year in (999, 10000, 2026.5):
			with self.subTest(year=year), self.assertRaises(ValueError):
				normalize_identifiers({"kenya_kjsea_year": year})
		self.assertEqual(normalize_identifiers({"kenya_kjsea_year": "2026"})["kenya_kjsea_year"], 2026)

	def test_empty_optional_identifiers_stay_empty(self):
		self.assertIsNone(normalize_identifiers({"kenya_kemis_uli": " "})["kenya_kemis_uli"])
