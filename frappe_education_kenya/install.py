"""
Frappe Education Kenya — Installation & Setup Module

Handles app installation, post-install configuration, and migration tasks.
Creates custom fields on Frappe Education DocTypes, seeds initial data,
and configures role permissions.
"""

import frappe
from frappe import _

from frappe_education_kenya.workspace_home import merge_home


def before_install():
	"""
	Pre-installation checks.
	Verify that frappe/education is installed.
	"""
	if not frappe.db.exists("Module Def", "Education"):
		frappe.throw(
			_(
				"Frappe Education app is required but not installed. "
				"Please install it first: bench get-app education && bench --site [site] install-app education"
			)
		)
	create_roles()


def after_install():
	"""
	Post-installation setup.
	Creates custom fields, seeds data, and configures the app.
	"""
	frappe.logger().info("Starting Frappe Education Kenya installation...")

	try:
		create_custom_fields()
		seed_cbc_grading_scale()
		seed_meal_types()
		seed_student_categories()
		create_roles()
		seed_cbc_levels()
		seed_kenya_counties()
		seed_moe_templates()
		create_default_settings()
		from frappe_education_kenya.school_operations import setup

		setup()
		merge_home()

		frappe.db.commit()
		frappe.logger().info("Frappe Education Kenya installation completed successfully.")

	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(f"Frappe Education Kenya installation failed: {e!s}")
		raise


def after_migrate():
	"""
	Post-migration tasks.
	Ensures custom fields exist after framework upgrades.
	"""
	create_roles()
	create_custom_fields()
	seed_cbc_grading_scale()
	seed_meal_types()
	seed_student_categories()
	from frappe_education_kenya.school_operations import setup

	setup()
	merge_home()
	frappe.db.commit()


def create_custom_fields():
	"""
	Create custom fields on existing Frappe Education DocTypes.
	These extend Student, Assessment Result, Fee Structure, and other core DocTypes
	with Kenya-specific fields.
	"""
	custom_fields = {
		"Student": [
			{
				"fieldname": "kenya_section",
				"label": "Kenya Education Details",
				"fieldtype": "Section Break",
				"insert_after": "student_email_id",
				"collapsible": 1,
			},
			{
				"fieldname": "kenya_upin",
				"label": "UPIN (Unique Personal Identifier)",
				"fieldtype": "Data",
				"insert_after": "kenya_section",
				"description": "NEMIS Unique Personal Identification Number",
			},
			{
				"fieldname": "kenya_nemis_number",
				"label": "NEMIS Number",
				"fieldtype": "Data",
				"insert_after": "kenya_upin",
			},
			{
				"fieldname": "kenya_birth_certificate_no",
				"label": "Birth Certificate Number",
				"fieldtype": "Data",
				"insert_after": "kenya_nemis_number",
			},
			{
				"fieldname": "kenya_cbc_level",
				"label": "CBC Level",
				"fieldtype": "Link",
				"options": "CBC Level",
				"insert_after": "kenya_birth_certificate_no",
			},
			{
				"fieldname": "kenya_column_break_1",
				"label": "",
				"fieldtype": "Column Break",
				"insert_after": "kenya_cbc_level",
			},
			{
				"fieldname": "kenya_special_needs_category",
				"label": "Special Needs Category",
				"fieldtype": "Select",
				"options": "\nNone\nPhysical Disability\nVisual Impairment\nHearing Impairment\nIntellectual Disability\nAutism Spectrum\nMultiple Disabilities\nLearning Difficulty\nSpeech and Language Disorder",
				"insert_after": "kenya_column_break_1",
			},
			{
				"fieldname": "kenya_orphan_status",
				"label": "Orphan Status",
				"fieldtype": "Select",
				"options": "\nNot Applicable\nPartial Orphan (One parent deceased)\nTotal Orphan (Both parents deceased)",
				"insert_after": "kenya_special_needs_category",
			},
			{
				"fieldname": "kenya_boarder_status",
				"label": "Boarder Status",
				"fieldtype": "Select",
				"options": "\nDay Scholar\nBoarder\nQuarter Boarder\nWeekly Boarder",
				"insert_after": "kenya_orphan_status",
			},
			{
				"fieldname": "kenya_column_break_2",
				"label": "",
				"fieldtype": "Column Break",
				"insert_after": "kenya_boarder_status",
			},
			{
				"fieldname": "kenya_county",
				"label": "County of Residence",
				"fieldtype": "Link",
				"options": "Kenya County",
				"insert_after": "kenya_column_break_2",
			},
			{
				"fieldname": "kenya_sub_county",
				"label": "Sub-County",
				"fieldtype": "Link",
				"options": "Kenya Sub County",
				"insert_after": "kenya_county",
			},
			{
				"fieldname": "kenya_ward",
				"label": "Ward",
				"fieldtype": "Data",
				"insert_after": "kenya_sub_county",
			},
			{
				"fieldname": "kenya_section_transport",
				"label": "Transport & Meals",
				"fieldtype": "Section Break",
				"insert_after": "kenya_ward",
				"collapsible": 1,
			},
			{
				"fieldname": "kenya_transport_route",
				"label": "Transport Route",
				"fieldtype": "Link",
				"options": "Transport Route",
				"insert_after": "kenya_section_transport",
			},
			{
				"fieldname": "kenya_meal_programme",
				"label": "Enrolled in Meal Programme",
				"fieldtype": "Check",
				"insert_after": "kenya_transport_route",
			},
			{
				"fieldname": "kenya_dietary_requirements",
				"label": "Dietary Requirements",
				"fieldtype": "Text",
				"insert_after": "kenya_meal_programme",
			},
		],
		"Assessment Result": [
			{
				"fieldname": "cbc_performance_level",
				"label": "CBC Performance Level",
				"fieldtype": "Select",
				"options": "\nPL1 - Exceeds Expectations\nPL2 - Meets Expectations\nPL3 - Approaches Expectations\nPL4 - Below Expectations",
				"insert_after": "total_score",
			},
			{
				"fieldname": "cbc_competence_statement",
				"label": "Competence Statement",
				"fieldtype": "Text",
				"insert_after": "cbc_performance_level",
			},
		],
		"Fee Structure": [
			{
				"fieldname": "kenya_fee_section",
				"label": "Kenya Fee Details",
				"fieldtype": "Section Break",
				"insert_after": "program",
				"collapsible": 1,
			},
			{
				"fieldname": "kenya_cbc_level",
				"label": "CBC Level",
				"fieldtype": "Link",
				"options": "CBC Level",
				"insert_after": "kenya_fee_section",
			},
			{
				"fieldname": "kenya_fee_category",
				"label": "Fee Category",
				"fieldtype": "Select",
				"options": "\nTuition Fee\nActivity Fee\nExamination Fee\nDevelopment Fund\nMaintenance Fee\nLibrary Fee\nLaboratory Fee\nSports Fee\nComputer/ICT Fee\nTransport Fee\nMeals Fee\nBoarding Fee\nOther",
				"insert_after": "kenya_cbc_level",
			},
			{
				"fieldname": "kenya_is_government_regulated",
				"label": "Is Government Regulated",
				"fieldtype": "Check",
				"insert_after": "kenya_fee_category",
			},
		],
		"Assessment Plan": [
			{
				"fieldname": "cbc_section",
				"label": "CBC Curriculum",
				"fieldtype": "Section Break",
				"insert_after": "academic_term",
				"collapsible": 1,
			},
			{
				"fieldname": "cbc_level",
				"label": "CBC Level",
				"fieldtype": "Link",
				"options": "CBC Level",
				"insert_after": "cbc_section",
			},
			{
				"fieldname": "cbc_learning_area",
				"label": "CBC Learning Area",
				"fieldtype": "Link",
				"options": "CBC Learning Area",
				"insert_after": "cbc_level",
			},
			{
				"fieldname": "cbc_strand",
				"label": "CBC Strand",
				"fieldtype": "Link",
				"options": "CBC Strand",
				"insert_after": "cbc_learning_area",
			},
			{
				"fieldname": "cbc_column_break",
				"fieldtype": "Column Break",
				"insert_after": "cbc_strand",
			},
			{
				"fieldname": "cbc_sub_strand",
				"label": "CBC Sub-Strand",
				"fieldtype": "Link",
				"options": "CBC Sub Strand",
				"insert_after": "cbc_column_break",
			},
			{
				"fieldname": "cbc_assessment_method",
				"label": "Assessment Method",
				"fieldtype": "Select",
				"options": "\nObservation\nOral/Aural\nWritten\nPractical\nProject\nPortfolio",
				"insert_after": "cbc_sub_strand",
			},
		],
		"Course": [
			{
				"fieldname": "cbc_learning_area",
				"label": "CBC Learning Area",
				"fieldtype": "Link",
				"options": "CBC Learning Area",
				"insert_after": "department",
			},
		],
		"Topic": [
			{
				"fieldname": "cbc_section",
				"label": "CBC Curriculum",
				"fieldtype": "Section Break",
				"insert_after": "hero_image",
			},
			{
				"fieldname": "cbc_level",
				"label": "CBC Level",
				"fieldtype": "Link",
				"options": "CBC Level",
				"insert_after": "cbc_section",
			},
			{
				"fieldname": "cbc_strand",
				"label": "CBC Strand",
				"fieldtype": "Link",
				"options": "CBC Strand",
				"depends_on": "eval:doc.cbc_level",
				"link_filters": '[["CBC Strand", "cbc_level", "=", "eval:doc.cbc_level"]]',
				"insert_after": "cbc_level",
			},
			{
				"fieldname": "cbc_sub_strand",
				"label": "CBC Sub-Strand",
				"fieldtype": "Link",
				"options": "CBC Sub Strand",
				"depends_on": "eval:doc.cbc_strand",
				"link_filters": '[["CBC Sub Strand", "strand", "=", "eval:doc.cbc_strand"]]',
				"insert_after": "cbc_strand",
			},
		],
		"Program": [
			{
				"fieldname": "cbc_level_mapping",
				"label": "CBC Level",
				"fieldtype": "Link",
				"options": "CBC Level",
				"insert_after": "department",
			},
		],
		"Education Settings": [
			{
				"fieldname": "kenya_tab_communications",
				"label": "Communications",
				"fieldtype": "Tab Break",
				"insert_after": "school_college_logo",
			},
			{
				"fieldname": "kenya_pledge_reminder_days",
				"label": "Pledge Reminder Days Before Due",
				"fieldtype": "Int",
				"default": "3",
				"non_negative": 1,
				"insert_after": "kenya_tab_communications",
			},
			{
				"fieldname": "kenya_enable_pledge_reminders",
				"label": "Enable Pledge Reminders",
				"fieldtype": "Check",
				"default": "0",
				"insert_after": "kenya_pledge_reminder_days",
			},
			{
				"fieldname": "kenya_enable_scheduled_messages",
				"label": "Enable Scheduled Messages",
				"fieldtype": "Check",
				"default": "0",
				"insert_after": "kenya_enable_pledge_reminders",
			},
		],
	}

	for doctype, fields in custom_fields.items():
		for field in fields:
			if not frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": field["fieldname"]}):
				doc = frappe.new_doc("Custom Field")
				doc.dt = doctype
				doc.__dict__.update(field)
				doc.save()
				frappe.logger().info(f"Created custom field {field['fieldname']} on {doctype}")


def create_roles():
	"""Create Kenya-specific roles if they don't exist."""
	roles = [
		{"role_name": "Transport Manager", "desk_access": 1},
		{"role_name": "Catering Manager", "desk_access": 1},
		{"role_name": "MoE Reporter", "desk_access": 1},
		{"role_name": "Kitchen Staff", "desk_access": 1},
		{"role_name": "Academic Admin", "desk_access": 1},
		{"role_name": "Librarian", "desk_access": 1},
		{"role_name": "Bursar", "desk_access": 1},
		{"role_name": "Head Teacher", "desk_access": 1},
		{"role_name": "Education Manager", "desk_access": 1},
	]

	for role_data in roles:
		if not frappe.db.exists("Role", role_data["role_name"]):
			role = frappe.new_doc("Role")
			role.__dict__.update(role_data)
			role.save()
			frappe.logger().info(f"Created role: {role_data['role_name']}")


def seed_cbc_levels():
	"""Seed the CBC Level structure (2-6-3-3 system)."""
	cbc_levels = [
		{
			"level_code": "ECDE_PP1",
			"level_name": "Pre-Primary 1",
			"education_sector": "Pre-Primary",
			"years_of_study": 1,
			"sequence_order": 1,
			"moef_level_code": "PP1",
			"is_transition_level": 0,
		},
		{
			"level_code": "ECDE_PP2",
			"level_name": "Pre-Primary 2",
			"education_sector": "Pre-Primary",
			"years_of_study": 1,
			"sequence_order": 2,
			"moef_level_code": "PP2",
			"is_transition_level": 0,
		},
		{
			"level_code": "PRI_G1",
			"level_name": "Grade 1",
			"education_sector": "Primary",
			"years_of_study": 1,
			"sequence_order": 3,
			"moef_level_code": "G1",
			"is_transition_level": 0,
		},
		{
			"level_code": "PRI_G2",
			"level_name": "Grade 2",
			"education_sector": "Primary",
			"years_of_study": 1,
			"sequence_order": 4,
			"moef_level_code": "G2",
			"is_transition_level": 0,
		},
		{
			"level_code": "PRI_G3",
			"level_name": "Grade 3",
			"education_sector": "Primary",
			"years_of_study": 1,
			"sequence_order": 5,
			"moef_level_code": "G3",
			"is_transition_level": 0,
		},
		{
			"level_code": "PRI_G4",
			"level_name": "Grade 4",
			"education_sector": "Primary",
			"years_of_study": 1,
			"sequence_order": 6,
			"moef_level_code": "G4",
			"is_transition_level": 0,
		},
		{
			"level_code": "PRI_G5",
			"level_name": "Grade 5",
			"education_sector": "Primary",
			"years_of_study": 1,
			"sequence_order": 7,
			"moef_level_code": "G5",
			"is_transition_level": 0,
		},
		{
			"level_code": "PRI_G6",
			"level_name": "Grade 6",
			"education_sector": "Primary",
			"years_of_study": 1,
			"sequence_order": 8,
			"moef_level_code": "G6",
			"is_transition_level": 1,
			"examination_body": "KNAT",
			"national_exam_name": "KPSEA",
		},
		{
			"level_code": "JSS_G7",
			"level_name": "Grade 7",
			"education_sector": "Junior Secondary",
			"years_of_study": 1,
			"sequence_order": 9,
			"moef_level_code": "G7",
			"is_transition_level": 0,
		},
		{
			"level_code": "JSS_G8",
			"level_name": "Grade 8",
			"education_sector": "Junior Secondary",
			"years_of_study": 1,
			"sequence_order": 10,
			"moef_level_code": "G8",
			"is_transition_level": 0,
		},
		{
			"level_code": "JSS_G9",
			"level_name": "Grade 9",
			"education_sector": "Junior Secondary",
			"years_of_study": 1,
			"sequence_order": 11,
			"moef_level_code": "G9",
			"is_transition_level": 1,
			"examination_body": "KNAT",
			"national_exam_name": "KJSEA",
		},
		{
			"level_code": "SSS_G10",
			"level_name": "Grade 10",
			"education_sector": "Senior Secondary",
			"years_of_study": 1,
			"sequence_order": 12,
			"moef_level_code": "G10",
			"is_transition_level": 0,
		},
		{
			"level_code": "SSS_G11",
			"level_name": "Grade 11",
			"education_sector": "Senior Secondary",
			"years_of_study": 1,
			"sequence_order": 13,
			"moef_level_code": "G11",
			"is_transition_level": 0,
		},
		{
			"level_code": "SSS_G12",
			"level_name": "Grade 12",
			"education_sector": "Senior Secondary",
			"years_of_study": 1,
			"sequence_order": 14,
			"moef_level_code": "G12",
			"is_transition_level": 1,
			"examination_body": "KNEC",
			"national_exam_name": "KACSE",
		},
	]

	for level in cbc_levels:
		if not frappe.db.exists("CBC Level", level["level_code"]):
			doc = frappe.new_doc("CBC Level")
			doc.__dict__.update(level)
			doc.is_standard_fixture = 1
			doc.save()


def seed_kenya_counties():
	"""Seed Kenya's 47 counties with codes."""
	counties = [
		("001", "Mombasa", "Coast", "Mombasa"),
		("002", "Kwale", "Coast", "Kwale"),
		("003", "Kilifi", "Coast", "Kilifi"),
		("004", "Tana River", "Coast", "Hola"),
		("005", "Lamu", "Coast", "Lamu"),
		("006", "Taita-Taveta", "Coast", "Voi"),
		("007", "Garissa", "North Eastern", "Garissa"),
		("008", "Wajir", "North Eastern", "Wajir"),
		("009", "Mandera", "North Eastern", "Mandera"),
		("010", "Marsabit", "Eastern", "Marsabit"),
		("011", "Isiolo", "Eastern", "Isiolo"),
		("012", "Meru", "Eastern", "Meru"),
		("013", "Tharaka-Nithi", "Eastern", "Chuka"),
		("014", "Embu", "Eastern", "Embu"),
		("015", "Kitui", "Eastern", "Kitui"),
		("016", "Machakos", "Eastern", "Machakos"),
		("017", "Makueni", "Eastern", "Wote"),
		("018", "Nyandarua", "Central", "Ol Kalou"),
		("019", "Nyeri", "Central", "Nyeri"),
		("020", "Kirinyaga", "Central", "Kerugoya"),
		("021", "Murang'a", "Central", "Murang'a"),
		("022", "Kiambu", "Central", "Kiambu"),
		("023", "Turkana", "Rift Valley", "Lodwar"),
		("024", "West Pokot", "Rift Valley", "Kapenguria"),
		("025", "Samburu", "Rift Valley", "Maralal"),
		("026", "Trans Nzoia", "Rift Valley", "Kitale"),
		("027", "Uasin Gishu", "Rift Valley", "Eldoret"),
		("028", "Elgeyo-Marakwet", "Rift Valley", "Iten"),
		("029", "Nandi", "Rift Valley", "Kapsabet"),
		("030", "Baringo", "Rift Valley", "Kabarnet"),
		("031", "Laikipia", "Rift Valley", "Nanyuki"),
		("032", "Nakuru", "Rift Valley", "Nakuru"),
		("033", "Narok", "Rift Valley", "Narok"),
		("034", "Kajiado", "Rift Valley", "Kajiado"),
		("035", "Kericho", "Rift Valley", "Kericho"),
		("036", "Bomet", "Rift Valley", "Bomet"),
		("037", "Kakamega", "Western", "Kakamega"),
		("038", "Vihiga", "Western", "Vihiga"),
		("039", "Bungoma", "Western", "Bungoma"),
		("040", "Busia", "Western", "Busia"),
		("041", "Siaya", "Nyanza", "Siaya"),
		("042", "Kisumu", "Nyanza", "Kisumu"),
		("043", "Homa Bay", "Nyanza", "Homa Bay"),
		("044", "Migori", "Nyanza", "Migori"),
		("045", "Kisii", "Nyanza", "Kisii"),
		("046", "Nyamira", "Nyanza", "Nyamira"),
		("047", "Nairobi", "Nairobi", "Nairobi"),
	]

	for code, name, region, capital in counties:
		if not frappe.db.exists("Kenya County", code):
			doc = frappe.new_doc("Kenya County")
			doc.county_code = code
			doc.county_name = name
			doc.region = region
			doc.capital_town = capital
			doc.save()


def seed_moe_templates():
	"""Seed standard MoE return templates."""
	templates = [
		{
			"template_code": "EMIS-001",
			"template_name": "Enrolment by Grade and Sex",
			"return_type": "Enrolment",
			"frequency": "Termly",
			"due_date_rule": "End of term + 14 days",
			"reminder_days_before": 7,
			"responsible_role": "Academic Admin",
			"is_standard_template": 1,
			"nemis_upload_format": 1,
			"description": "Report total enrolment by grade and gender for MoE EMIS",
		},
		{
			"template_code": "EMIS-002",
			"template_name": "Teacher Establishment & Deployment",
			"return_type": "Staff",
			"frequency": "Annual",
			"due_date_rule": "31st March",
			"reminder_days_before": 14,
			"responsible_role": "Academic Admin",
			"is_standard_template": 1,
			"nemis_upload_format": 1,
			"description": "Report teaching and non-teaching staff establishment",
		},
		{
			"template_code": "EMIS-003",
			"template_name": "Learners with Special Needs",
			"return_type": "Special Needs",
			"frequency": "Termly",
			"due_date_rule": "End of term + 14 days",
			"reminder_days_before": 7,
			"responsible_role": "Academic Admin",
			"is_standard_template": 1,
			"nemis_upload_format": 1,
			"description": "Report learners with special needs by category and grade",
		},
		{
			"template_code": "EMIS-004",
			"template_name": "Orphaned and Vulnerable Children",
			"return_type": "Orphans & Vulnerable",
			"frequency": "Termly",
			"due_date_rule": "End of term + 14 days",
			"reminder_days_before": 7,
			"responsible_role": "Academic Admin",
			"is_standard_template": 1,
			"nemis_upload_format": 1,
			"description": "Report OVC learners by orphan status and grade",
		},
		{
			"template_code": "EMIS-005",
			"template_name": "Infrastructure and Facilities",
			"return_type": "Infrastructure",
			"frequency": "Annual",
			"due_date_rule": "30th June",
			"reminder_days_before": 14,
			"responsible_role": "Academic Admin",
			"is_standard_template": 1,
			"nemis_upload_format": 1,
			"description": "Report school infrastructure, classrooms, and facilities",
		},
		{
			"template_code": "EMIS-006",
			"template_name": "Examination Results Summary",
			"return_type": "Examination",
			"frequency": "Annual",
			"due_date_rule": "30 days after results release",
			"reminder_days_before": 7,
			"responsible_role": "Academic Admin",
			"is_standard_template": 1,
			"nemis_upload_format": 1,
			"description": "Report national examination results summary",
		},
		{
			"template_code": "EMIS-007",
			"template_name": "Financial Returns (Public Schools)",
			"return_type": "Financial",
			"frequency": "Annual",
			"due_date_rule": "31st July",
			"reminder_days_before": 14,
			"responsible_role": "Bursar",
			"is_standard_template": 1,
			"nemis_upload_format": 0,
			"description": "Annual financial returns for public schools",
		},
		{
			"template_code": "EMIS-008",
			"template_name": "Daily Attendance Summary",
			"return_type": "Attendance",
			"frequency": "Daily",
			"due_date_rule": "Daily by 5pm",
			"reminder_days_before": 0,
			"responsible_role": "Academic Admin",
			"is_standard_template": 1,
			"nemis_upload_format": 1,
			"description": "Daily attendance summary for EMIS",
		},
		{
			"template_code": "EMIS-009",
			"template_name": "Boarder vs Day Scholar Ratio",
			"return_type": "Boarders",
			"frequency": "Termly",
			"due_date_rule": "End of term + 14 days",
			"reminder_days_before": 7,
			"responsible_role": "Academic Admin",
			"is_standard_template": 1,
			"nemis_upload_format": 1,
			"description": "Report boarder vs day scholar distribution by grade",
		},
		{
			"template_code": "EMIS-010",
			"template_name": "School Feeding Programme Returns",
			"return_type": "School Feeding",
			"frequency": "Termly",
			"due_date_rule": "End of term + 14 days",
			"reminder_days_before": 7,
			"responsible_role": "Catering Manager",
			"is_standard_template": 1,
			"nemis_upload_format": 1,
			"description": "Report school feeding programme participation and meals served",
		},
	]

	for template in templates:
		if not frappe.db.exists("MoE Return Template", template["template_code"]):
			doc = frappe.new_doc("MoE Return Template")
			doc.__dict__.update(template)
			doc.save()


def create_default_settings():
	"""Create default settings documents."""
	if not frappe.db.exists("Education Kenya Settings", "Education Kenya Settings"):
		settings = frappe.new_doc("Education Kenya Settings")
		settings.school_name = "Your School Name"
		settings.school_code = "SCH001"
		settings.school_type = "Public (Day)"
		settings.enable_cbc_assessments = 1
		settings.enable_transport = 0
		settings.enable_meals = 0
		settings.enable_moe_compliance = 0
		settings.default_currency = "KES"
		settings.require_upin = 1
		settings.require_nemis_number = 1
		settings.track_special_needs = 1
		settings.track_boarding_status = 1
		settings.save()


def seed_student_categories():
	"""Ensure the Student Categories that Fee Structures, Fee Schedules and enrollments bill by exist.

	The names equal the `Student.kenya_boarder_status` options, so an enrollment can copy its
	student's boarder status straight into `student_category`. Idempotent.
	"""
	for category in ("Day Scholar", "Boarder", "Quarter Boarder", "Weekly Boarder"):
		if not frappe.db.exists("Student Category", category):
			frappe.get_doc({"doctype": "Student Category", "category": category}).insert(
				ignore_permissions=True
			)


def seed_meal_types():
	"""Seed the standard Kenyan school meal types (masters for Table MultiSelect).

	Backs Meal Programme.meal_types and Student Meal Subscription.included_meals.
	Idempotent.
	"""
	if not frappe.db.exists("DocType", "Meal Type"):
		return
	for meal_type in ["Breakfast", "Mid-Morning Snack", "Lunch", "Evening Tea", "Dinner"]:
		if not frappe.db.exists("Meal Type", meal_type):
			doc = frappe.new_doc("Meal Type")
			doc.meal_type_name = meal_type
			doc.insert(ignore_permissions=True)


def seed_cbc_grading_scale():
	"""Model CBC Performance Levels (PL1-PL4) as a standard Grading Scale.

	This replaces the removed CBC Performance Level Rubric / CBC Assessment
	scoring engine: the score -> level bands live in a base Education Grading
	Scale, and assessments use the base Assessment Plan / Assessment Result.
	Idempotent.
	"""
	from frappe_education_kenya.frappe_education_kenya.assessment import CBC_GRADING_SCALE

	if frappe.db.exists("Grading Scale", CBC_GRADING_SCALE):
		return

	scale = frappe.new_doc("Grading Scale")
	scale.grading_scale_name = CBC_GRADING_SCALE
	scale.description = "Kenya CBC Performance Levels (PL1 Exceeds - PL4 Below Expectations)."
	for code, description, threshold in [
		("PL1", "Exceeds Expectations", 80),
		("PL2", "Meets Expectations", 65),
		("PL3", "Approaches Expectations", 50),
		("PL4", "Below Expectations", 0),
	]:
		scale.append(
			"intervals",
			{"grade_code": code, "grade_description": description, "threshold": threshold},
		)
	scale.insert(ignore_permissions=True)
	scale.submit()
