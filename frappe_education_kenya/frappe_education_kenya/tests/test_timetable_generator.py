"""Pure timetable solver checks; no Frappe site or database."""

import unittest

from frappe_education_kenya.frappe_education_kenya.doctype.timetable_run.generator import overlaps, solve


def period(name, start, end, day="Mon", is_break=0):
	return {"name": name, "day": day, "start_time": start, "end_time": end, "is_break": is_break}


def requirement(name, instructor, group="G1", lessons=1, max_per_day=1, room="R1"):
	return {
		"name": name,
		"instructor": instructor,
		"student_group": group,
		"course": "C",
		"lessons_per_week": lessons,
		"max_per_day": max_per_day,
		"room": room,
	}


def block(instructor, period_name, day="Mon"):
	return {"instructor": instructor, "day": day, "period": period_name, "type": "Time Off"}


class TestTimetableGenerator(unittest.TestCase):
	def test_partial_time_overlap_is_a_resource_clash(self):
		periods = [period("P1", "08:00", "08:40"), period("P2", "08:20", "09:00")]
		reqs = [requirement("A", "X", "G1", room=None), requirement("B", "X", "G2", room=None)]
		result = solve(reqs, periods, rooms=["R1", "R2"])
		self.assertEqual(len(result["slots"]), 1)
		self.assertEqual([c["requirement"] for c in result["conflicts"]], ["B"])

		result = solve(reqs, [*periods, period("P3", "09:00", "09:40")], rooms=["R1", "R2"])
		self.assertFalse(result["conflicts"])
		first, second = result["slots"]
		self.assertFalse(overlaps(first, second))

	def test_availability_breaks_and_daily_limit(self):
		periods = [
			period("P1", "08:00", "08:40"),
			period("BR", "08:30", "09:00", is_break=1),
			period("P2", "09:00", "09:40"),
			period("P3", "10:00", "10:40"),
		]
		result = solve([requirement("A", "X", lessons=2)], periods, [block("X", "P2")])
		self.assertEqual([s["period"] for s in result["slots"]], ["P3"])
		self.assertEqual(len(result["conflicts"]), 1)

	def test_bounded_backtracking_repairs_greedy_choice_deterministically(self):
		periods = [period(f"P{i}", f"{7 + i:02d}:00", f"{7 + i:02d}:40") for i in range(1, 5)]
		reqs = [requirement(name, f"I{name}") for name in "ABCD"]
		blocks = [
			block("IA", "P3"),
			block("IA", "P4"),
			block("IB", "P1"),
			block("IB", "P4"),
			block("IC", "P1"),
			block("IC", "P2"),
			block("ID", "P3"),
			block("ID", "P4"),
		]
		greedy = solve(reqs, periods, blocks, max_backtracks=0)
		self.assertEqual([c["requirement"] for c in greedy["conflicts"]], ["D"])
		repaired = solve(reqs, periods, blocks, max_backtracks=1000)
		self.assertFalse(repaired["conflicts"])
		self.assertGreater(repaired["backtracks"], 0)
		self.assertLessEqual(repaired["backtracks"], 1000)
		self.assertEqual(repaired, solve(list(reversed(reqs)), list(reversed(periods)), blocks))

	def test_invalid_inputs_raise(self):
		with self.assertRaises(ValueError):
			solve([], [], max_backtracks=-1)
		with self.assertRaises(ValueError):
			solve([], [period("P1", "09:00", "08:00")])
		with self.assertRaises(ValueError):
			solve([], [period("P1", "08:00", "09:00")], [block("X", "P1", day="Tue")])


if __name__ == "__main__":
	unittest.main()
