"""
Frappe Education Kenya — Desktop Icon Configuration

Defines the app icon shown on the Frappe desktop/apps page.
"""

from frappe import _


def get_data():
    return [
        {
            "module_name": "Frappe Education Kenya",
            "color": "#006600",
            "icon": "octicon octicon-mortar-board",
            "type": "module",
            "label": _("Education Kenya"),
            "description": "Kenya CBC-aligned education management with MoE compliance",
            "category": "Modules",
        }
    ]
