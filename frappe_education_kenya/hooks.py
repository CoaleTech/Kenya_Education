"""
Frappe Education Kenya — App Configuration

A custom Frappe application that extends Frappe Education with full alignment
to Kenya's Competency-Based Curriculum (CBC) and Ministry of Education compliance.

Covers: ECDE (2 years), Primary (6 years), Junior Secondary (3 years),
        Senior Secondary (3 years) — the full 2-6-3-3 structure.

Modules:
    - CBC Curriculum: Learning areas, strands, assessments, performance levels
    - Transport Management: Routes, vehicles, student subscriptions
    - Meals & Food Services: Feeding programmes, daily records, subscriptions
    - MoE Compliance: Automated EMIS/NEMIS reporting and return submissions
    - Student Lifecycle: Kenya-specific student data, transitions, special needs
"""

from . import __version__ as app_version

app_name = "frappe_education_kenya"
app_title = "Education Kenya"
app_publisher = "Frappe Education Kenya Team"
app_description = "Kenya CBC-aligned education management with MoE compliance, transport, and meals"
app_email = "dev@frappeeducationkenya.com"
app_license = "mit"

# ──────────────────────────────────────────────────────────────────────────────
# REQUIRED APPS
# ──────────────────────────────────────────────────────────────────────────────
# This app extends frappe/education — it MUST be installed ("frappe" is implicit)
required_apps = ["erpnext", "education"]

# ──────────────────────────────────────────────────────────────────────────────
# DESK ASSETS
# ──────────────────────────────────────────────────────────────────────────────
# Bundles compiled by frappe's esbuild pipeline from:
#   public/js/education_kenya.bundle.js
#   public/scss/education_kenya.bundle.scss
app_include_js = "education_kenya.bundle.js"
app_include_css = "education_kenya.bundle.css"

# ──────────────────────────────────────────────────────────────────────────────
# DESKTOP ICONS & WORKSPACES
# ──────────────────────────────────────────────────────────────────────────────
#
# SINGLE DESK SURFACE + SINGLE HOME. Frappe Education is the primary app; this
# app localises it. We deliberately do NOT register an app tile (no
# `add_to_apps_screen`) and do NOT ship a second sidebar or a second workspace.
# Instead, on install and every migrate:
#   * install.setup_unified_navigation() folds Kenya links into the shared
#     "Education" sidebar and suppresses the auto standalone Kenya tile/sidebar;
#   * workspace_home.merge_kenya_home_into_education() injects the Kenya CBC
#     analytics (number cards + charts) and navigation into the single
#     "Education" workspace home, then retires the standalone "Kenya Education"
#     workspace.
# Do NOT add `add_to_apps_screen` or ship a workspace JSON here — either would
# recreate a second, competing desk home.
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# DOC EVENTS — Server Scripts
# ──────────────────────────────────────────────────────────────────────────────
# Hooks that run on DocType events to enforce CBC logic and MoE compliance

doc_events = {
	# When a Student is created/updated, validate Kenya-specific fields
	"Student": {
		"validate": "frappe_education_kenya.frappe_education_kenya.doctype.cbc_student_settings.cbc_student_settings.validate_student_kenya_fields",
		"on_update": "frappe_education_kenya.frappe_education_kenya.doctype.cbc_student_settings.cbc_student_settings.sync_student_to_nemis_fields",
	},
	# On save, tag the base Assessment Result with its CBC Performance Level,
	# resolved from the "CBC Performance Levels" grading scale.
	"Assessment Result": {
		"validate": "frappe_education_kenya.frappe_education_kenya.assessment.map_assessment_to_performance_level",
	},
	# When a Fee Structure is created, auto-add transport/meal components if applicable
	"Fee Structure": {
		"validate": "frappe_education_kenya.frappe_education_kenya.doctype.cbc_fee_settings.cbc_fee_settings.validate_kenya_fee_structure",
	},
	# When Program Enrollment happens, auto-create CBC level progression record
	"Program Enrollment": {
		"on_submit": "frappe_education_kenya.frappe_education_kenya.doctype.student_transition.student_transition.after_program_enrollment",
	},
}

# ──────────────────────────────────────────────────────────────────────────────
# SCHEDULED TASKS
# ──────────────────────────────────────────────────────────────────────────────
# Background jobs for MoE reporting, reminders, and data maintenance

scheduler_events = {
	"daily": [
		# Check for upcoming MoE report deadlines and notify responsible staff
		"frappe_education_kenya.frappe_education_kenya.doctype.moe_return_submission.moe_return_submission.check_upcoming_deadlines",
		# Generate daily attendance summary for MoE reporting
		"frappe_education_kenya.frappe_education_kenya.doctype.moe_return_submission.moe_return_submission.generate_daily_attendance_snapshot",
	],
	"weekly": [
		# Validate NEMIS data completeness and flag incomplete records
		"frappe_education_kenya.frappe_education_kenya.doctype.cbc_student_settings.cbc_student_settings.validate_nemis_data_completeness",
	],
	"monthly": [
		# Auto-generate monthly MoE enrolment return draft
		"frappe_education_kenya.frappe_education_kenya.doctype.moe_return_submission.moe_return_submission.auto_generate_monthly_enrolment_return",
	],
	"cron": {
		# Transport insurance and inspection expiry checks — every Monday at 8am
		"0 8 * * 1": [
			"frappe_education_kenya.frappe_education_kenya.doctype.transport_vehicle.transport_vehicle.check_vehicle_compliance",
		],
	},
}

# ──────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────────────────────────────────────
# Seed data exported with the app — CBC curriculum, MoE templates, counties, etc.

fixtures = [
	# CBC Curriculum fixtures
	{"dt": "CBC Level", "filters": [["is_standard_fixture", "=", 1]]},
	{"dt": "CBC Learning Area", "filters": [["is_standard_fixture", "=", 1]]},
	{"dt": "CBC Strand", "filters": [["is_standard_fixture", "=", 1]]},
	{"dt": "CBC Sub Strand", "filters": [["is_standard_fixture", "=", 1]]},
	{"dt": "CBC Learning Outcome", "filters": [["is_standard_fixture", "=", 1]]},
	# MoE Compliance fixtures
	{"dt": "MoE Return Template", "filters": [["is_standard_template", "=", 1]]},
	# Kenya geographic data
	{"dt": "Kenya County", "filters": []},
	{"dt": "Kenya Sub County", "filters": []},
	# Kenya-specific settings
	{"dt": "Education Kenya Settings", "filters": []},
	# Custom fields (exported as Property Setters)
	"Custom Field",
	"Property Setter",
]

# ──────────────────────────────────────────────────────────────────────────────
# BEFORE INSTALL / AFTER INSTALL
# ──────────────────────────────────────────────────────────────────────────────

before_install = "frappe_education_kenya.install.before_install"
after_install = "frappe_education_kenya.install.after_install"
after_migrate = "frappe_education_kenya.install.after_migrate"

# ──────────────────────────────────────────────────────────────────────────────
# PERMISSIONS
# ──────────────────────────────────────────────────────────────────────────────

has_permission = {
	"Transport Route": "frappe_education_kenya.frappe_education_kenya.permissions.has_transport_permission",
	"Transport Vehicle": "frappe_education_kenya.frappe_education_kenya.permissions.has_transport_permission",
	"Daily Meal Record": "frappe_education_kenya.frappe_education_kenya.permissions.has_meals_permission",
	"MoE Return Submission": "frappe_education_kenya.frappe_education_kenya.permissions.has_moe_permission",
}

# ──────────────────────────────────────────────────────────────────────────────
# JINJA FILTERS (for report templates)
# ──────────────────────────────────────────────────────────────────────────────

jinja = {
	"methods": [
		"frappe_education_kenya.frappe_education_kenya.utils.jinja_filters.format_moe_date",
		"frappe_education_kenya.frappe_education_kenya.utils.jinja_filters.format_nemis_id",
		"frappe_education_kenya.frappe_education_kenya.utils.jinja_filters.performance_level_label",
		"frappe_education_kenya.frappe_education_kenya.utils.jinja_filters.cbc_level_name",
	]
}

# ──────────────────────────────────────────────────────────────────────────────
# TRANSLATIONS
# ──────────────────────────────────────────────────────────────────────────────
# Translation CSVs live in frappe_education_kenya/translations/<lang>.csv
# (Kiswahili contributions welcome). No hook is needed for these.
