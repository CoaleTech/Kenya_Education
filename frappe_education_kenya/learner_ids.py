"""Kenyan learner identifiers and their restricted Student fields."""

from decimal import Decimal, InvalidOperation

import frappe
from frappe import _

IDENTIFIER_ROLES = {"Academic Admin", "Head Teacher", "Education Manager"}
FIELDS = (
	"kenya_kemis_uli",
	"kenya_sha_number",
	"kenya_kjsea_year",
	"kenya_kjsea_assessment_no",
	"kenya_kjsea_score",
)


def normalize_identifiers(values: dict) -> dict:
	result = dict(values)
	for field in ("kenya_kemis_uli", "kenya_sha_number", "kenya_kjsea_assessment_no"):
		if field in result:
			result[field] = str(result[field]).strip() or None if result[field] is not None else None
	for field, minimum, maximum in (("kenya_kjsea_year", 1000, 9999), ("kenya_kjsea_score", 0, 500)):
		value = result.get(field)
		if value in (None, "") or (field == "kenya_kjsea_year" and value == 0):
			continue
		try:
			number = Decimal(str(value))
			if (
				not number.is_finite()
				or number != number.to_integral_value()
				or not minimum <= number <= maximum
			):
				raise ValueError(field)
		except (InvalidOperation, ValueError):
			raise ValueError(field) from None
		result[field] = int(number)
	return result


def validate_identifiers(doc, method=None):
	try:
		values = normalize_identifiers({field: doc.get(field) for field in FIELDS})
	except ValueError as error:
		frappe.throw(
			_("{0} must be a whole number in its allowed range (year: 1000–9999; score: 0–500).").format(
				doc.meta.get_label(str(error))
			)
		)
	if frappe.session.user != "Administrator" and not IDENTIFIER_ROLES.intersection(frappe.get_roles()):
		before = doc.get_doc_before_save()
		previous = normalize_identifiers({field: before.get(field) if before else None for field in FIELDS})
		for field in FIELDS:
			old, new = previous.get(field), values.get(field)
			if field in ("kenya_kjsea_year", "kenya_kjsea_score"):
				old, new = old or 0, new or 0
			if old != new:
				frappe.throw(
					_(
						"Only Academic Admin, Head Teacher or Education Manager may change Kenyan learner identifiers."
					),
					frappe.PermissionError,
				)
	for field, value in values.items():
		doc.set(field, value)


def setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
	from frappe.permissions import add_permission, update_permission_property

	definitions = (
		("kenya_kemis_uli", "KEMIS Unique Learner ID", "Data", {"unique": 1}),
		("kenya_sha_number", "SHA Number", "Data", {}),
		("kenya_kjsea_year", "KJSEA Year", "Int", {}),
		("kenya_kjsea_assessment_no", "KJSEA Assessment Number", "Data", {}),
		("kenya_kjsea_score", "KJSEA Score", "Int", {"description": "Whole number from 0 to 500."}),
	)
	fields = []
	after = "kenya_dietary_requirements"
	for fieldname, label, fieldtype, options in definitions:
		fields.append(
			{
				"fieldname": fieldname,
				"label": label,
				"fieldtype": fieldtype,
				"permlevel": 1,
				"insert_after": after,
				**options,
			}
		)
		after = fieldname
	create_custom_fields({"Student": fields}, update=True)
	for role in sorted(IDENTIFIER_ROLES):
		for level in (0, 1):
			add_permission("Student", role, permlevel=level)
			for permission in ("read", "write"):
				update_permission_property("Student", role, level, permission, 1, validate=False)
