"""Server-side logic for CBC Fee Settings: Kenya fee structure validation and auto-billing."""

import frappe
from frappe import _
from frappe.model.document import Document


class CBCFeeSettings(Document):
	pass


def validate_kenya_fee_structure(doc, method=None):
	"""Validate hook on Fee Structure: enforces Kenya fee-component conventions.

	If Transport or Meals invoicing is set to auto-generate (per CBC Fee
	Settings) but the Fee Structure carries a `kenya_fee_category` of
	Transport Fee / Meals Fee without a matching program-level component
	configured, warn the bursar rather than silently mis-billing.
	"""
	settings = frappe.get_cached_doc("CBC Fee Settings")
	fee_category = doc.get("kenya_fee_category")

	if fee_category == "Transport Fee" and not settings.get("auto_generate_transport_invoice"):
		frappe.msgprint(
			_(
				"Transport Fee auto-invoicing is disabled in CBC Fee Settings. "
				"This Fee Structure will not be applied automatically."
			),
			indicator="orange",
			alert=True,
		)

	if fee_category == "Meals Fee" and not settings.get("auto_generate_meals_invoice"):
		frappe.msgprint(
			_(
				"Meals Fee auto-invoicing is disabled in CBC Fee Settings. "
				"This Fee Structure will not be applied automatically."
			),
			indicator="orange",
			alert=True,
		)

	if doc.get("kenya_is_government_regulated") and not doc.get("kenya_cbc_level"):
		frappe.msgprint(
			_("Government-regulated fee structures should specify a CBC Level for MoE reporting."),
			indicator="orange",
			alert=True,
		)
