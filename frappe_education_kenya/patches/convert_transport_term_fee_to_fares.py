"""Preserve legacy transport fares after the new child schema has synced."""

from frappe_education_kenya.transport import convert_transport_term_fee_to_fares


def execute():
	convert_transport_term_fee_to_fares()
