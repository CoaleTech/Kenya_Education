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
app_publisher = "CoaleTech"
app_description = "Kenya CBC-aligned education management with MoE compliance, transport, and meals"
app_email = "support@coale.tech"
app_license = "gpl-3.0"

# ──────────────────────────────────────────────────────────────────────────────
# REQUIRED APPS
# ──────────────────────────────────────────────────────────────────────────────
# This app extends frappe/education — it MUST be installed ("frappe" is implicit)
required_apps = ["frappe/erpnext", "frappe/education"]

# ──────────────────────────────────────────────────────────────────────────────
# DESK ASSETS
# ──────────────────────────────────────────────────────────────────────────────
# Bundle compiled by frappe's esbuild pipeline from public/js/education_kenya.bundle.js.
# No app stylesheet: Desk surfaces use the Espresso tokens as shipped.
app_include_js = "education_kenya.bundle.js"

# ──────────────────────────────────────────────────────────────────────────────
# DESKTOP ICONS & WORKSPACES
# ──────────────────────────────────────────────────────────────────────────────
#
# ONE SIDEBAR, SHARED WITH EDUCATION. Frappe Education is the primary app; this app
# localises it, so it has no app tile (no `add_to_apps_screen`), no dock entry and no
# sidebar of its own. Its navigation lives inside the Education sidebar:
#   * fixtures/custom_sidebar.json  a site-layer `Custom Sidebar` on the Education
#     module whose rows are all `added`, so Desk appends them after Education's own
#     rows and Education upgrades still reach the sidebar (`frappe.desk.layers`);
#   * home.json + workspace_home.py the CBC number cards, charts (<module>/number_card,
#     <module>/dashboard_chart, all `is_standard`), shortcuts and link cards, folded
#     into Education's own Home on install and migrate (it is not a standard
#     workspace, so it has no site layer).
# `code_only_modules` below tells Desk this module ships no navigation and names
# Education as its heir, so Kenya doctypes open inside the Education sidebar.
# Nothing here edits the Education app's own sidebar or workspace.
# Do NOT add `add_to_apps_screen`: it would give this app a second tile.
# ──────────────────────────────────────────────────────────────────────────────

code_only_modules = {"Frappe Education Kenya": ["Education"]}

# ──────────────────────────────────────────────────────────────────────────────
# DOC EVENTS — Server Scripts
# ──────────────────────────────────────────────────────────────────────────────
# Hooks that run on DocType events to enforce CBC logic and MoE compliance

doc_events = {
	# When a Student is created/updated, validate Kenya-specific fields
	"Student": {
		"validate": "frappe_education_kenya.frappe_education_kenya.doctype.education_kenya_settings.education_kenya_settings.validate_student_kenya_fields",
		"on_update": "frappe_education_kenya.frappe_education_kenya.doctype.education_kenya_settings.education_kenya_settings.sync_student_to_nemis_fields",
	},
	# On save, tag the base Assessment Result with its CBC Performance Level,
	# resolved from the "CBC Performance Levels" grading scale.
	"Assessment Result": {
		"validate": [
			"frappe_education_kenya.frappe_education_kenya.assessment.map_assessment_to_performance_level",
			"frappe_education_kenya.parent_ops.validate_result_publication",
		],
		# validate does not run for edits of submitted documents.
		"before_update_after_submit": "frappe_education_kenya.parent_ops.validate_result_publication",
	},
	"Course Schedule": {
		"validate": "frappe_education_kenya.timetable.protect_course_schedule",
		"on_trash": "frappe_education_kenya.timetable.protect_course_schedule",
	},
	"Question": {
		"validate": "frappe_education_kenya.teaching.protect_question",
		"on_trash": "frappe_education_kenya.teaching.protect_question",
	},
	"Topic": {"validate": "frappe_education_kenya.teaching.validate_topic_curriculum"},
	"Payment Entry": {
		"validate": "frappe_education_kenya.bursary.validate_payment",
		"before_submit": "frappe_education_kenya.bursary.before_payment_submit",
		"on_submit": [
			"frappe_education_kenya.bursary.payment_rollup",
			"frappe_education_kenya.messaging.fee_payment_notifications",
		],
		"on_cancel": "frappe_education_kenya.bursary.payment_rollup",
	},
	# Fee Structure save: require a Student Category and warn on Kenya fee conventions.
	# Nothing adds transport/meal components for you; add them as Fee Components.
	"Fee Structure": {
		"validate": "frappe_education_kenya.billing.validate_kenya_fee_structure",
	},
	# Fee Schedule save: its category must be set and match its Fee Structure's
	"Fee Schedule": {
		"validate": "frappe_education_kenya.billing.validate_schedule_category",
	},
	# Program Enrollment: default the Student Category from the boarder status on save;
	# on submit/cancel record or reverse its CBC level transition
	"Program Enrollment": {
		"validate": "frappe_education_kenya.billing.set_enrollment_category",
		"on_submit": "frappe_education_kenya.frappe_education_kenya.doctype.student_transition.student_transition.after_program_enrollment",
		"on_cancel": "frappe_education_kenya.frappe_education_kenya.doctype.student_transition.student_transition.after_program_enrollment_cancel",
	},
}

# ──────────────────────────────────────────────────────────────────────────────
# SCHEDULED TASKS
# ──────────────────────────────────────────────────────────────────────────────
# Background jobs for MoE reporting, reminders, and data maintenance

scheduler_events = {
	"hourly": [
		"frappe_education_kenya.teaching.release_exam_papers",
	],
	"daily": [
		"frappe_education_kenya.bursary.daily_reminders",
		# Check for upcoming MoE report deadlines and notify responsible staff
		"frappe_education_kenya.frappe_education_kenya.doctype.moe_return_submission.moe_return_submission.check_upcoming_deadlines",
		# Generate daily attendance summary for MoE reporting
		"frappe_education_kenya.frappe_education_kenya.doctype.moe_return_submission.moe_return_submission.generate_daily_attendance_snapshot",
	],
	"weekly": [
		# Validate NEMIS data completeness and flag incomplete records
		"frappe_education_kenya.frappe_education_kenya.doctype.education_kenya_settings.education_kenya_settings.validate_nemis_data_completeness",
	],
	"monthly": [
		# Auto-generate monthly MoE enrolment return draft
		"frappe_education_kenya.frappe_education_kenya.doctype.moe_return_submission.moe_return_submission.auto_generate_monthly_enrolment_return",
	],
	"cron": {
		"*/5 * * * *": [
			"frappe_education_kenya.messaging.dispatch_due",
		],
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
	# Kenya links appended to the Education sidebar (site layer, module Education)
	{"dt": "Custom Sidebar", "filters": [["module", "=", "Education"], ["user", "is", "not set"]]},
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
	"Library Circulation": "frappe_education_kenya.library.circulation_has_permission",
	"Library Copy": "frappe_education_kenya.library.copy_has_permission",
	"Timetable Availability": "frappe_education_kenya.timetable.availability_permission",
	"Guardian Consent": "frappe_education_kenya.parent_ops.consent_permission",
	"Student Pathway Choice": "frappe_education_kenya.pathways.choice_has_permission",
	"Scheme of Work": "frappe_education_kenya.teaching.preparation_permission",
	"Lesson Plan": "frappe_education_kenya.teaching.preparation_permission",
	"Exam Paper": "frappe_education_kenya.teaching.preparation_permission",
	"Question": "frappe_education_kenya.teaching.question_permission",
	"Quiz": "frappe_education_kenya.teaching.quiz_permission",
	"File": "frappe_education_kenya.teaching.file_permission",
	"Fee Pledge": "frappe_education_kenya.bursary.guardian_finance_permission",
	"Bursary Award": "frappe_education_kenya.bursary.guardian_finance_permission",
}

permission_query_conditions = {
	"Library Circulation": "frappe_education_kenya.library.circulation_query_conditions",
	"Library Copy": "frappe_education_kenya.library.copy_query_conditions",
	"Guardian Consent": "frappe_education_kenya.parent_ops.consent_query",
	"Student Pathway Choice": "frappe_education_kenya.pathways.choice_query_conditions",
	"Scheme of Work": "frappe_education_kenya.teaching.scheme_query",
	"Lesson Plan": "frappe_education_kenya.teaching.lesson_query",
	"Exam Paper": "frappe_education_kenya.teaching.paper_query",
	"Question": "frappe_education_kenya.teaching.question_query",
	"Quiz": "frappe_education_kenya.teaching.quiz_query",
	"File": "frappe_education_kenya.teaching.file_query",
	"Fee Pledge": "frappe_education_kenya.bursary.fee_pledge_query",
	"Bursary Award": "frappe_education_kenya.bursary.bursary_award_query",
}

extend_doctype_class = {
	"File": ["frappe_education_kenya.teaching.ExamFileMixin"],
	"Quiz": ["frappe_education_kenya.teaching.ExamQuizMixin"],
}

on_session_creation = ["frappe_education_kenya.parent_ops.on_session_creation"]

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
