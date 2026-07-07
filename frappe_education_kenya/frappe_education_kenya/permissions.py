"""Permission query hooks for Frappe Education Kenya operational DocTypes.

These are registered under `has_permission` in hooks.py and gate row-level
access to Transport, Meals, and MoE Compliance records so that only staff
with the relevant Kenya role can view or edit them.
"""

import frappe



def has_transport_permission(doc, user=None, permission_type=None):
	"""Restrict Transport Route / Transport Vehicle access to transport staff."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	allowed_roles = {"System Manager", "Kenya System Administrator", "Head Teacher", "Transport Manager"}
	if _user_has_role_for(user, allowed_roles):
		return True
	return False


def has_meals_permission(doc, user=None, permission_type=None):
	"""Restrict Daily Meal Record access to catering/head teacher staff."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	allowed_roles = {"System Manager", "Kenya System Administrator", "Head Teacher", "Catering Manager"}
	if _user_has_role_for(user, allowed_roles):
		return True
	return False


def has_moe_permission(doc, user=None, permission_type=None):
	"""Restrict MoE Return Submission access to reporting-authorized staff."""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	allowed_roles = {"System Manager", "Kenya System Administrator", "Head Teacher", "MoE Reporter"}
	if _user_has_role_for(user, allowed_roles):
		return True
	return False


def _user_has_role_for(user, allowed_roles):
	user_roles = set(frappe.get_roles(user))
	return bool(user_roles.intersection(allowed_roles))
