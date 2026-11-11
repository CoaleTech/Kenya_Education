"""Timetable generation/publication against real Education records (rolled back)."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from frappe_education_kenya import timetable

YEAR = "EDK TT 2031"
TERM = f"{YEAR} (TT1)"


def _get_or_insert(doctype, filters, values):
	name = frappe.db.get_value(doctype, filters)
	return name or frappe.get_doc({"doctype": doctype, **filters, **values}).insert().name


class TestTimetablePublish(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.get_meta("Course Schedule").has_field("timetable_run"):
			timetable.setup()

	def setUp(self):
		if not frappe.db.get_single_value("Education Settings", "instructor_created_by"):
			frappe.db.set_single_value("Education Settings", "instructor_created_by", "Full Name")
		frappe.set_user("Administrator")
		_get_or_insert(
			"Academic Year",
			{"academic_year_name": YEAR},
			{"year_start_date": "2031-01-01", "year_end_date": "2031-12-31"},
		)
		_get_or_insert(
			"Academic Term",
			{"academic_year": YEAR, "term_name": "TT1"},
			{"term_start_date": "2031-01-06", "term_end_date": "2031-01-19"},
		)
		self.instructor = _get_or_insert("Instructor", {"instructor_name": "EDK TT Instructor"}, {})
		self.course = _get_or_insert("Course", {"course_name": "EDK TT Course"}, {})
		self.room = _get_or_insert("Room", {"room_name": "EDK TT Room"}, {})
		self.group = _get_or_insert(
			"Student Group",
			{"student_group_name": "EDK TT Group"},
			{"academic_year": YEAR, "academic_term": TERM, "group_based_on": "Activity"},
		)
		self.period = _get_or_insert(
			"Timetable Period", {"day": "Mon", "start_time": "07:00:00"}, {"end_time": "07:40:00"}
		)
		self.requirement = frappe.get_doc(
			{
				"doctype": "Timetable Requirement",
				"student_group": self.group,
				"course": self.course,
				"instructor": self.instructor,
				"lessons_per_week": 1,
				"max_per_day": 1,
				"room": self.room,
			}
		).insert()

	def tearDown(self):
		frappe.db.rollback()

	def _run(self):
		run = frappe.get_doc({"doctype": "Timetable Run", "academic_term": TERM}).insert().name
		self.assertTrue(timetable._generate(run)["ok"])
		return run

	def _schedules(self, run):
		return frappe.get_all(
			"Course Schedule", filters={"timetable_run": run}, pluck="schedule_date", order_by="schedule_date"
		)

	def test_publish_uses_term_dates_and_replaces_only_unlinked_prior_rows(self):
		first = self._run()
		timetable._publish(first)
		self.assertEqual(
			[getdate(d) for d in self._schedules(first)], [getdate("2031-01-06"), getdate("2031-01-13")]
		)
		self.assertEqual(frappe.db.get_value("Timetable Run", first, "status"), "Published")

		second = self._run()
		timetable._publish(second)
		self.assertFalse(self._schedules(first))
		self.assertEqual(len(self._schedules(second)), 2)
		self.assertEqual(timetable._publish(second)["message"], frappe._("Timetable already published"))
		self.assertEqual(len(self._schedules(second)), 2)

	def test_republish_rejects_linked_prior_rows_without_partial_changes(self):
		first = self._run()
		timetable._publish(first)
		schedule = frappe.get_all("Course Schedule", filters={"timetable_run": first}, pluck="name", limit=1)[
			0
		]
		frappe.get_doc(
			{
				"doctype": "Student Attendance",
				"name": "EDK-TT-LINK",
				"naming_series": "EDU-ATT-.YYYY.-",
				"student": "EDK-TT-NOT-VALIDATED",
				"course_schedule": schedule,
				"date": "2031-01-06",
				"status": "Present",
			}
		).db_insert()

		second = self._run()
		with self.assertRaises(frappe.LinkExistsError):
			timetable._publish(second)
		self.assertEqual(len(self._schedules(first)), 2)
		self.assertFalse(self._schedules(second))
		self.assertEqual(frappe.db.get_value("Timetable Run", second, "status"), "Generated")

	def test_conflicts_and_stale_inputs_block_publication(self):
		frappe.db.set_value("Timetable Requirement", self.requirement.name, "lessons_per_week", 2)
		run = self._run()
		conflicts = frappe.get_doc("Timetable Run", run).conflicts
		self.assertEqual([c.requirement for c in conflicts], [self.requirement.name])
		with self.assertRaises(frappe.ValidationError):
			timetable._publish(run)

		frappe.db.set_value("Timetable Requirement", self.requirement.name, "lessons_per_week", 1)
		run = self._run()
		frappe.db.set_value("Timetable Requirement", self.requirement.name, "lessons_per_week", 2)
		with self.assertRaises(frappe.ValidationError):
			timetable._publish(run)

	def test_published_schedule_rows_and_run_are_protected(self):
		run = self._run()
		timetable._publish(run)
		schedule = frappe.get_doc("Course Schedule", {"timetable_run": run})
		schedule.room = self.room
		with self.assertRaises(frappe.ValidationError):
			schedule.save()
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Course Schedule", schedule.name)
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Timetable Run", run)
