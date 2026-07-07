"""
Patch: Create Custom Fields on Student DocType

Adds Kenya-specific custom fields to the existing Student DocType from Frappe Education.
This patch ensures the fields exist even if the install script was interrupted.
"""

import frappe


def execute():
    """Create custom fields on Student DocType."""
    from frappe_education_kenya.install import create_custom_fields
    create_custom_fields()
