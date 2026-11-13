"""Delete the stored values of the CBC Fee Settings fields that nothing read.

The fields were removed from the DocType; their `tabSingles` rows would otherwise linger.
"""

import frappe


def execute():
	frappe.db.delete("Singles", {"doctype": "CBC Fee Settings"})
