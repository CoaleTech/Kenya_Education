"""
Patch: Seed CBC Curriculum Learning Areas

Populates the CBC Learning Area DocType with standard Kenyan curriculum subjects
across all levels of the 2-6-3-3 system.
"""

import frappe


def execute():
	"""Seed CBC Learning Areas with standard curriculum subjects."""
	learning_areas = [
		# Pre-Primary
		{
			"code": "PP-LA-01",
			"name": "Language Activities (English)",
			"category": "Languages",
			"core": 1,
			"examinable": 0,
			"levels": ["ECDE_PP1", "ECDE_PP2"],
		},
		{
			"code": "PP-LA-02",
			"name": "Language Activities (Kiswahili)",
			"category": "Languages",
			"core": 1,
			"examinable": 0,
			"levels": ["ECDE_PP1", "ECDE_PP2"],
		},
		{
			"code": "PP-MA-01",
			"name": "Mathematical Activities",
			"category": "Mathematics",
			"core": 1,
			"examinable": 0,
			"levels": ["ECDE_PP1", "ECDE_PP2"],
		},
		{
			"code": "PP-EN-01",
			"name": "Environmental Activities",
			"category": "Sciences",
			"core": 1,
			"examinable": 0,
			"levels": ["ECDE_PP1", "ECDE_PP2"],
		},
		{
			"code": "PP-PS-01",
			"name": "Psychomotor and Creative Activities",
			"category": "Creative Arts",
			"core": 1,
			"examinable": 0,
			"levels": ["ECDE_PP1", "ECDE_PP2"],
		},
		{
			"code": "PP-RE-01",
			"name": "Religious Education Activities",
			"category": "Religious Education",
			"core": 1,
			"examinable": 0,
			"levels": ["ECDE_PP1", "ECDE_PP2"],
		},
		# Lower Primary (Grade 1-3)
		{
			"code": "LP-EN-01",
			"name": "English Language",
			"category": "Languages",
			"core": 1,
			"examinable": 1,
			"levels": ["PRI_G1", "PRI_G2", "PRI_G3"],
		},
		{
			"code": "LP-KI-01",
			"name": "Kiswahili Language",
			"category": "Languages",
			"core": 1,
			"examinable": 1,
			"levels": ["PRI_G1", "PRI_G2", "PRI_G3"],
		},
		{
			"code": "LP-IL-01",
			"name": "Indigenous Language",
			"category": "Languages",
			"core": 1,
			"examinable": 0,
			"levels": ["PRI_G1", "PRI_G2", "PRI_G3"],
		},
		{
			"code": "LP-MA-01",
			"name": "Mathematics",
			"category": "Mathematics",
			"core": 1,
			"examinable": 1,
			"levels": ["PRI_G1", "PRI_G2", "PRI_G3"],
		},
		{
			"code": "LP-EV-01",
			"name": "Environmental Activities",
			"category": "Sciences",
			"core": 1,
			"examinable": 0,
			"levels": ["PRI_G1", "PRI_G2", "PRI_G3"],
		},
		{
			"code": "LP-HN-01",
			"name": "Hygiene and Nutrition Activities",
			"category": "Life Skills",
			"core": 1,
			"examinable": 0,
			"levels": ["PRI_G1", "PRI_G2", "PRI_G3"],
		},
		{
			"code": "LP-RE-01",
			"name": "Religious Education (CRE/IRE/HRE)",
			"category": "Religious Education",
			"core": 1,
			"examinable": 0,
			"levels": ["PRI_G1", "PRI_G2", "PRI_G3"],
		},
		{
			"code": "LP-MC-01",
			"name": "Movement and Creative Activities",
			"category": "Creative Arts",
			"core": 1,
			"examinable": 0,
			"levels": ["PRI_G1", "PRI_G2", "PRI_G3"],
		},
		# Upper Primary (Grade 4-6)
		{
			"code": "UP-EN-01",
			"name": "English Language",
			"category": "Languages",
			"core": 1,
			"examinable": 1,
			"levels": ["PRI_G4", "PRI_G5", "PRI_G6"],
		},
		{
			"code": "UP-KI-01",
			"name": "Kiswahili Language",
			"category": "Languages",
			"core": 1,
			"examinable": 1,
			"levels": ["PRI_G4", "PRI_G5", "PRI_G6"],
		},
		{
			"code": "UP-MA-01",
			"name": "Mathematics",
			"category": "Mathematics",
			"core": 1,
			"examinable": 1,
			"levels": ["PRI_G4", "PRI_G5", "PRI_G6"],
		},
		{
			"code": "UP-SC-01",
			"name": "Science and Technology",
			"category": "Sciences",
			"core": 1,
			"examinable": 1,
			"levels": ["PRI_G4", "PRI_G5", "PRI_G6"],
		},
		{
			"code": "UP-AG-01",
			"name": "Agriculture",
			"category": "Technical",
			"core": 1,
			"examinable": 1,
			"levels": ["PRI_G4", "PRI_G5", "PRI_G6"],
		},
		{
			"code": "UP-HS-01",
			"name": "Home Science",
			"category": "Life Skills",
			"core": 1,
			"examinable": 1,
			"levels": ["PRI_G4", "PRI_G5", "PRI_G6"],
		},
		{
			"code": "UP-SS-01",
			"name": "Social Studies",
			"category": "Humanities",
			"core": 1,
			"examinable": 1,
			"levels": ["PRI_G4", "PRI_G5", "PRI_G6"],
		},
		{
			"code": "UP-RE-01",
			"name": "Religious Education (CRE/IRE/HRE)",
			"category": "Religious Education",
			"core": 1,
			"examinable": 1,
			"levels": ["PRI_G4", "PRI_G5", "PRI_G6"],
		},
		{
			"code": "UP-CA-01",
			"name": "Creative Arts",
			"category": "Creative Arts",
			"core": 1,
			"examinable": 0,
			"levels": ["PRI_G4", "PRI_G5", "PRI_G6"],
		},
		{
			"code": "UP-PE-01",
			"name": "Physical and Health Education",
			"category": "Physical Education",
			"core": 1,
			"examinable": 0,
			"levels": ["PRI_G4", "PRI_G5", "PRI_G6"],
		},
		# Junior Secondary (Grade 7-9)
		{
			"code": "JS-EN-01",
			"name": "English",
			"category": "Languages",
			"core": 1,
			"examinable": 1,
			"levels": ["JSS_G7", "JSS_G8", "JSS_G9"],
		},
		{
			"code": "JS-KI-01",
			"name": "Kiswahili",
			"category": "Languages",
			"core": 1,
			"examinable": 1,
			"levels": ["JSS_G7", "JSS_G8", "JSS_G9"],
		},
		{
			"code": "JS-MA-01",
			"name": "Mathematics",
			"category": "Mathematics",
			"core": 1,
			"examinable": 1,
			"levels": ["JSS_G7", "JSS_G8", "JSS_G9"],
		},
		{
			"code": "JS-IS-01",
			"name": "Integrated Science",
			"category": "Sciences",
			"core": 1,
			"examinable": 1,
			"levels": ["JSS_G7", "JSS_G8", "JSS_G9"],
		},
		{
			"code": "JS-SS-01",
			"name": "Social Studies",
			"category": "Humanities",
			"core": 1,
			"examinable": 1,
			"levels": ["JSS_G7", "JSS_G8", "JSS_G9"],
		},
		{
			"code": "JS-RE-01",
			"name": "Religious Education (CRE/IRE/HRE)",
			"category": "Religious Education",
			"core": 1,
			"examinable": 1,
			"levels": ["JSS_G7", "JSS_G8", "JSS_G9"],
		},
		{
			"code": "JS-BS-01",
			"name": "Business Studies",
			"category": "Humanities",
			"core": 1,
			"examinable": 1,
			"levels": ["JSS_G7", "JSS_G8", "JSS_G9"],
		},
		{
			"code": "JS-AG-01",
			"name": "Agriculture",
			"category": "Technical",
			"core": 1,
			"examinable": 1,
			"levels": ["JSS_G7", "JSS_G8", "JSS_G9"],
		},
		{
			"code": "JS-LS-01",
			"name": "Life Skills",
			"category": "Life Skills",
			"core": 1,
			"examinable": 0,
			"levels": ["JSS_G7", "JSS_G8", "JSS_G9"],
		},
		{
			"code": "JS-SP-01",
			"name": "Sports and Physical Health",
			"category": "Physical Education",
			"core": 1,
			"examinable": 0,
			"levels": ["JSS_G7", "JSS_G8", "JSS_G9"],
		},
		{
			"code": "JS-CA-01",
			"name": "Creative Arts and Sports",
			"category": "Creative Arts",
			"core": 1,
			"examinable": 0,
			"levels": ["JSS_G7", "JSS_G8", "JSS_G9"],
		},
		{
			"code": "JS-PR-01",
			"name": "Pre-Technical Studies",
			"category": "Technical",
			"core": 1,
			"examinable": 1,
			"levels": ["JSS_G7", "JSS_G8", "JSS_G9"],
		},
		# Senior Secondary - Core (Grade 10-12)
		{
			"code": "SS-EN-01",
			"name": "English",
			"category": "Languages",
			"core": 1,
			"examinable": 1,
			"levels": ["SSS_G10", "SSS_G11", "SSS_G12"],
		},
		{
			"code": "SS-KI-01",
			"name": "Kiswahili",
			"category": "Languages",
			"core": 1,
			"examinable": 1,
			"levels": ["SSS_G10", "SSS_G11", "SSS_G12"],
		},
		{
			"code": "SS-MA-01",
			"name": "Mathematics",
			"category": "Mathematics",
			"core": 1,
			"examinable": 1,
			"levels": ["SSS_G10", "SSS_G11", "SSS_G12"],
		},
		{
			"code": "SS-LS-01",
			"name": "Life Skills",
			"category": "Life Skills",
			"core": 1,
			"examinable": 0,
			"levels": ["SSS_G10", "SSS_G11", "SSS_G12"],
		},
		# Senior Secondary - STEM Pathway
		{
			"code": "SS-PH-01",
			"name": "Physics",
			"category": "Sciences",
			"core": 0,
			"examinable": 1,
			"levels": ["SSS_G10", "SSS_G11", "SSS_G12"],
		},
		{
			"code": "SS-CH-01",
			"name": "Chemistry",
			"category": "Sciences",
			"core": 0,
			"examinable": 1,
			"levels": ["SSS_G10", "SSS_G11", "SSS_G12"],
		},
		{
			"code": "SS-BI-01",
			"name": "Biology",
			"category": "Sciences",
			"core": 0,
			"examinable": 1,
			"levels": ["SSS_G10", "SSS_G11", "SSS_G12"],
		},
		{
			"code": "SS-CS-01",
			"name": "Computer Science",
			"category": "Technical",
			"core": 0,
			"examinable": 1,
			"levels": ["SSS_G10", "SSS_G11", "SSS_G12"],
		},
		# Senior Secondary - Humanities Pathway
		{
			"code": "SS-HI-01",
			"name": "History",
			"category": "Humanities",
			"core": 0,
			"examinable": 1,
			"levels": ["SSS_G10", "SSS_G11", "SSS_G12"],
		},
		{
			"code": "SS-GE-01",
			"name": "Geography",
			"category": "Humanities",
			"core": 0,
			"examinable": 1,
			"levels": ["SSS_G10", "SSS_G11", "SSS_G12"],
		},
		{
			"code": "SS-EC-01",
			"name": "Economics",
			"category": "Humanities",
			"core": 0,
			"examinable": 1,
			"levels": ["SSS_G10", "SSS_G11", "SSS_G12"],
		},
		# Senior Secondary - Arts & Sports Pathway
		{
			"code": "SS-MU-01",
			"name": "Music",
			"category": "Creative Arts",
			"core": 0,
			"examinable": 1,
			"levels": ["SSS_G10", "SSS_G11", "SSS_G12"],
		},
		{
			"code": "SS-AR-01",
			"name": "Art and Design",
			"category": "Creative Arts",
			"core": 0,
			"examinable": 1,
			"levels": ["SSS_G10", "SSS_G11", "SSS_G12"],
		},
		{
			"code": "SS-PE-01",
			"name": "Physical Education",
			"category": "Physical Education",
			"core": 0,
			"examinable": 1,
			"levels": ["SSS_G10", "SSS_G11", "SSS_G12"],
		},
	]

	created = 0
	for area in learning_areas:
		if not frappe.db.exists("CBC Learning Area", area["code"]):
			doc = frappe.new_doc("CBC Learning Area")
			doc.learning_area_code = area["code"]
			doc.learning_area_name = area["name"]
			doc.learning_area_category = area["category"]
			doc.is_core = 1 if area["core"] else 0
			doc.is_examinable = 1 if area["examinable"] else 0
			doc.is_standard_fixture = 1

			for level_code in area["levels"]:
				doc.append("applicable_levels", {"cbc_level": level_code})

			doc.save()
			created += 1

	frappe.logger().info(f"Seeded {created} CBC Learning Areas")
