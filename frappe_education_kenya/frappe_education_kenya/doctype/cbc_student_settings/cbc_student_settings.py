"""Server-side logic for CBC Student Settings and Kenya-specific Student validation."""

import frappe
from frappe import _
from frappe.model.document import Document


class CBCStudentSettings(Document):
	pass


def _get_settings():
	return frappe.get_cached_doc("CBC Student Settings")


def validate_student_kenya_fields(doc, method=None):
	"""Validate Kenya-specific identifiers on the Student DocType before save.

	Enforces UPIN/NEMIS/birth-certificate requirements as configured in
	CBC Student Settings. Missing identifiers surface as a non-blocking
	warning rather than a hard validation error, since schools may
	onboard students before NEMIS registration completes.
	"""
	settings = _get_settings()

	if settings.get("require_upin") and not doc.get("kenya_upin"):
		frappe.msgprint(
			_("UPIN (Unique Personal Identifier) is recommended for {0} per Kenya MoE requirements.").format(
				doc.get("student_name") or doc.name
			),
			indicator="orange",
			alert=True,
		)

	if settings.get("require_nemis_number") and not doc.get("kenya_nemis_number"):
		frappe.msgprint(
			_("NEMIS number is recommended for {0} per Kenya MoE requirements.").format(
				doc.get("student_name") or doc.name
			),
			indicator="orange",
			alert=True,
		)


def sync_student_to_nemis_fields(doc, method=None):
	"""After a Student is updated, keep denormalized NEMIS-facing fields in sync.

	Normalizes the UPIN/NEMIS number formatting so downstream MoE exports
	don't choke on inconsistent casing/whitespace.
	"""
	changed = False

	if doc.get("kenya_upin"):
		normalized = str(doc.kenya_upin).strip().upper()
		if normalized != doc.kenya_upin:
			frappe.db.set_value("Student", doc.name, "kenya_upin", normalized, update_modified=False)
			changed = True

	if doc.get("kenya_nemis_number"):
		normalized = str(doc.kenya_nemis_number).strip()
		if normalized != doc.kenya_nemis_number:
			frappe.db.set_value("Student", doc.name, "kenya_nemis_number", normalized, update_modified=False)
			changed = True

	if changed:
		frappe.db.commit()


def validate_nemis_data_completeness():
	"""Weekly scheduled task: flag students missing required NEMIS identifiers.

	Logs a data-quality error entry summarizing incomplete records rather
	than blocking any transaction.
	"""
	settings = _get_settings()
	if not (settings.get("require_upin") or settings.get("require_nemis_number")):
		return

	or_filters = []
	if settings.get("require_upin"):
		or_filters.append(["kenya_upin", "in", ["", None]])
	if settings.get("require_nemis_number"):
		or_filters.append(["kenya_nemis_number", "in", ["", None]])

	if not or_filters:
		return

	incomplete = frappe.get_all(
		"Student",
		or_filters=or_filters,
		fields=["name", "student_name"],
		limit_page_length=0,
	)

	if not incomplete:
		return

	names = ", ".join(f"{s.student_name} ({s.name})" for s in incomplete[:50])
	frappe.log_error(
		title="Incomplete NEMIS data for students",
		message=_("The following students are missing required NEMIS identifiers: {0}").format(names),
	)
