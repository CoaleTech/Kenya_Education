"""Server-side logic for CBC Assessment: maps traditional scores to CBC Performance Levels."""

import frappe
from frappe.model.document import Document

# Default score-band -> Performance Level mapping, mirrors the CBC blueprint
# (PL1 Exceeds, PL2 Meets, PL3 Approaches, PL4 Below Expectations).
DEFAULT_PERFORMANCE_LEVEL_BANDS = [
	(80, 100, "PL1"),
	(65, 79.999, "PL2"),
	(50, 64.999, "PL3"),
	(0, 49.999, "PL4"),
]


class CBCAssessment(Document):
	pass


def _score_to_performance_level(percentage, criteria=None):
	"""Resolve a percentage score to a CBC performance level code.

	If the Assessment defines its own `performance_level_criteria` rubric
	rows, those take precedence over the default bands.
	"""
	bands = DEFAULT_PERFORMANCE_LEVEL_BANDS
	if criteria:
		custom_bands = []
		for row in criteria:
			lower = row.get("minimum_score")
			upper = row.get("maximum_score")
			level = row.get("performance_level")
			if lower is not None and upper is not None and level:
				custom_bands.append((lower, upper, level))
		if custom_bands:
			bands = custom_bands

	for lower, upper, level in bands:
		if lower <= percentage <= upper:
			return level
	return None


def map_assessment_to_performance_level(doc, method=None):
	"""Validate hook on Assessment Result: computes and stores the CBC performance level.

	Recomputes the percentage from total_score/maximum_score and stashes the
	resolved PL1-PL4 code on the document so downstream MoE reports and the
	student portal can display it directly.
	"""
	total_score = doc.get("total_score")
	maximum_score = doc.get("maximum_score")

	if total_score is None or not maximum_score:
		return

	try:
		percentage = (float(total_score) / float(maximum_score)) * 100
	except (TypeError, ZeroDivisionError, ValueError):
		return

	assessment_name = doc.get("assessment_group") or doc.get("assessment_plan")
	criteria = None
	if assessment_name and frappe.db.exists("CBC Assessment", assessment_name):
		criteria_doc = frappe.get_cached_doc("CBC Assessment", assessment_name)
		criteria = [row.as_dict() for row in criteria_doc.get("performance_level_criteria", [])]

	level = _score_to_performance_level(percentage, criteria)
	if level:
		doc.cbc_performance_level = level


def after_assessment_result_submit(doc, method=None):
	"""On-submit hook: increments the assessed-student counter on the linked CBC Assessment."""
	assessment_name = doc.get("assessment_group") or doc.get("assessment_plan")
	if not assessment_name or not frappe.db.exists("CBC Assessment", assessment_name):
		return

	current = frappe.db.get_value("CBC Assessment", assessment_name, "total_students_assessed") or 0
	frappe.db.set_value(
		"CBC Assessment",
		assessment_name,
		"total_students_assessed",
		current + 1,
		update_modified=False,
	)
