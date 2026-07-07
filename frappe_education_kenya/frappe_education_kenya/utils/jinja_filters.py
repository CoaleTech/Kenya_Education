"""Jinja template filters for Frappe Education Kenya report templates."""

import frappe


def format_moe_date(date_value):
	"""Format a date for MoE report templates (DD/MM/YYYY)."""
	if not date_value:
		return ""
	formatted = frappe.utils.formatdate(date_value, "dd/mm/yyyy")
	return formatted


def format_nemis_id(value):
	"""Normalize a NEMIS/UPIN identifier for display (uppercase, no whitespace)."""
	if not value:
		return ""
	return str(value).strip().upper()


PERFORMANCE_LEVEL_LABELS = {
	"PL1": "Exceeds Expectations",
	"PL2": "Meets Expectations",
	"PL3": "Approaches Expectations",
	"PL4": "Below Expectations",
}


def performance_level_label(level_code):
	"""Return the human-readable descriptor for a CBC performance level code."""
	return PERFORMANCE_LEVEL_LABELS.get(level_code, level_code or "")


def cbc_level_name(level_code):
	"""Resolve a CBC Level code to its human-readable name."""
	if not level_code:
		return ""
	name = frappe.db.get_value("CBC Level", {"level_code": level_code}, "level_name")
	return name or level_code
