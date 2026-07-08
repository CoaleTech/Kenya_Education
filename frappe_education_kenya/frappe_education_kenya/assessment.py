"""CBC assessment helpers.

CBC Performance Levels (PL1-PL4) are modelled as a standard Education
``Grading Scale`` ("CBC Performance Levels") instead of a parallel assessment
engine. Assessments therefore use the base ``Assessment Plan`` / ``Assessment
Result`` DocTypes; this module only maps a computed score to its Performance
Level and stores it on the ``cbc_performance_level`` custom field so MoE
reports and the parent/student portal can read it directly.

The score -> level bands live entirely in the grading scale (a base concept),
so there are no hard-coded thresholds here.
"""

import frappe
from frappe.utils import flt

CBC_GRADING_SCALE = "CBC Performance Levels"

# Presentation labels for the `cbc_performance_level` Select custom field.
# Keyed by the grading scale's grade codes; kept fixed so the stored value is
# always a valid Select option regardless of how a scale's free-text
# description is later edited.
PERFORMANCE_LEVEL_LABELS = {
	"PL1": "PL1 - Exceeds Expectations",
	"PL2": "PL2 - Meets Expectations",
	"PL3": "PL3 - Approaches Expectations",
	"PL4": "PL4 - Below Expectations",
}


def resolve_performance_level(percentage, grading_scale=CBC_GRADING_SCALE):
	"""Return the grade code (e.g. ``PL1``) for a percentage against a scale.

	Matches the highest interval whose threshold the percentage reaches, which
	mirrors ``education.education.api.get_grade`` without its request-scoped
	cache (that cache ignores the scale name on repeat calls within a request).
	"""
	intervals = frappe.get_all(
		"Grading Scale Interval",
		filters={"parent": grading_scale},
		fields=["grade_code", "threshold"],
	)
	for row in sorted(intervals, key=lambda r: flt(r.threshold), reverse=True):
		if flt(percentage) >= flt(row.threshold):
			return row.grade_code
	return None


def map_assessment_to_performance_level(doc, method=None):
	"""``validate`` hook on Assessment Result: store the CBC Performance Level.

	Runs after the core controller has computed ``total_score``; recomputes the
	percentage and resolves it against the "CBC Performance Levels" grading
	scale. No-op when the scale is absent or the scores are unusable.
	"""
	if not frappe.db.exists("Grading Scale", CBC_GRADING_SCALE):
		return

	total_score = doc.get("total_score")
	maximum_score = doc.get("maximum_score")
	if total_score is None or not maximum_score:
		return

	try:
		percentage = (float(total_score) / float(maximum_score)) * 100
	except (TypeError, ValueError, ZeroDivisionError):
		return

	code = resolve_performance_level(percentage)
	if code:
		doc.cbc_performance_level = PERFORMANCE_LEVEL_LABELS.get(code, code)
