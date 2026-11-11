"""Every role that can write one of our DocTypes must be able to search each editable Link target (Desk link fields)."""

import frappe
from frappe.desk.search import search_link
from frappe.tests import IntegrationTestCase

# Not tied to a writing form: administrative or portal roles.
SKIPPED_ROLES = {"System Manager", "Administrator", "Guest", "All", "Guardian", "Student"}


class TestLinkPermissions(IntegrationTestCase):
	def test_writing_roles_can_search_link_targets(self):
		frappe.flags.in_import = True  # User creation is throttled per hour
		modules = frappe.get_all("Module Def", filters={"app_name": "frappe_education_kenya"}, pluck="name")
		doctypes = [
			dt
			for dt in frappe.get_all("DocType", filters={"module": ["in", modules]}, pluck="name")
			if not frappe.get_meta(dt).istable and not frappe.get_meta(dt).issingle
		]
		roles = {
			p.role
			for dt in doctypes
			for p in frappe.get_meta(dt).permissions
			if (p.create or p.write) and p.role not in SKIPPED_ROLES
		}
		users = {}
		for index, role in enumerate(sorted(roles)):
			email = f"link-perm-{index}@example.invalid"
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "Link",
					"send_welcome_email": 0,
					"roles": [{"role": role}],
				}
			).insert(ignore_permissions=True)
			users[role] = email

		def can_search(target, user):
			frappe.set_user(user)
			try:
				search_link(target, "")
				return True
			except frappe.PermissionError:
				return False
			finally:
				frappe.set_user("Administrator")

		gaps = set()
		for dt in doctypes:
			meta = frappe.get_meta(dt)
			for role, user in users.items():
				if not (
					frappe.has_permission(dt, "create", user=user)
					or frappe.has_permission(dt, "write", user=user)
				):
					continue
				fields = list(meta.fields)
				for table in meta.get_table_fields():
					fields += frappe.get_meta(table.options).fields
				for df in fields:
					if df.fieldtype == "Link" and df.options != "DocType" and not df.read_only:
						if not can_search(df.options, user):
							gaps.add(f"{role} -> {df.options} ({dt}.{df.fieldname})")
		self.assertEqual(sorted(gaps), [])
