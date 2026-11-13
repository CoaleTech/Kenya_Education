"""Single idempotent post-sync entrypoint for the school operations domains.

Called from install.after_install and install.after_migrate, after DocType sync.
"""

from frappe_education_kenya import (
	bursary,
	collections,
	learner_ids,
	library,
	messaging,
	parent_ops,
	pathways,
	teaching,
	timetable,
)

# (doctype, role, permlevel, permission types). Merged into Custom DocPerm without removing existing rows.
GRANTS = (
	("Course Schedule", "Academic Admin", 0, ("read", "write", "create", "delete")),
	# Frappe requires a level-0 rule before any higher permlevel rule for the same role.
	("Assessment Result", "System Manager", 0, ("read",)),
	("Assessment Result", "Academic Admin", 0, ("read",)),
	("Assessment Result", "Head Teacher", 0, ("read",)),
	("Assessment Result", "System Manager", 1, ("read", "write")),
	("Assessment Result", "Academic Admin", 1, ("read", "write")),
	("Assessment Result", "Head Teacher", 1, ("read", "write")),
	("Payment Entry", "Bursar", 0, ("read", "write", "create", "submit", "cancel")),
	("Fees", "Bursar", 0, ("read",)),
	("Sales Invoice", "Bursar", 0, ("read",)),
	("Account", "Bursar", 0, ("read",)),
	("Cost Center", "Bursar", 0, ("read",)),
	("Mode of Payment", "Bursar", 0, ("read",)),
)

# Link fields need "select" on the target, or the Desk link search and validation fail with "Insufficient Permission".
# Roles that write one of our DocTypes get select on every doctype it links to. select exposes names/titles only.
LINK_SELECT = {
	"Academic Admin": (
		"Academic Term",
		"Academic Year",
		"Course",
		"Guardian",
		"Instructor",
		"Program",
		"Question",
		"Room",
		"Student Group",
	),
	"Bursar": ("Academic Term", "Customer", "Guardian", "Student"),
	"Catering Manager": ("Academic Term", "Student"),
	"Head Teacher": ("Academic Term", "Academic Year", "Course", "Employee", "Guardian", "Instructor"),
	"Instructor": ("Academic Term",),
	"Librarian": ("Article",),
	"Transport Manager": ("Academic Term", "Employee", "Student"),
}


def grant_permissions():
	from frappe.permissions import add_permission, update_permission_property

	link_grants = tuple(
		(doctype, role, 0, ("select",)) for role, doctypes in LINK_SELECT.items() for doctype in doctypes
	)
	for doctype, role, level, ptypes in GRANTS + link_grants:
		add_permission(doctype, role, permlevel=level)
		for ptype in ptypes:
			update_permission_property(doctype, role, level, ptype, 1, validate=False)


def setup():
	learner_ids.setup()
	library.setup()
	timetable.setup()
	parent_ops.setup()
	bursary.setup()
	collections.setup()
	pathways.setup()
	teaching.setup()
	messaging.setup()
	grant_permissions()
