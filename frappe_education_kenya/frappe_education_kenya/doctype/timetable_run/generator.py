"""Pure weekly solver; runnable without a Frappe site or database."""

from datetime import time, timedelta

DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def seconds(value):
	if isinstance(value, timedelta):
		return value.total_seconds()
	if isinstance(value, time):
		return value.hour * 3600 + value.minute * 60 + value.second
	parts = str(value).split(":")
	if len(parts) not in (2, 3):
		raise ValueError("Invalid time")
	hour, minute = int(parts[0]), int(parts[1])
	second = float(parts[2]) if len(parts) == 3 else 0
	if not (0 <= hour < 24 and 0 <= minute < 60 and 0 <= second < 60):
		raise ValueError("Invalid time")
	return hour * 3600 + minute * 60 + second


def overlaps(left, right):
	return (
		left["day"] == right["day"]
		and seconds(left["start_time"]) < seconds(right["end_time"])
		and seconds(right["start_time"]) < seconds(left["end_time"])
	)


def solve(requirements, periods, availability=(), rooms=(), max_backtracks=1000):
	"""Return every placed lesson and one conflict per unplaced lesson; never touch Frappe.

	Greedy seeds the best partial result. Iterative depth-first search repairs it,
	counting each undone choice against the configured bound (no recursion ceiling).
	"""
	if isinstance(max_backtracks, bool) or int(max_backtracks) != max_backtracks or max_backtracks < 0:
		raise ValueError("max_backtracks must be a nonnegative integer")
	periods = sorted(periods, key=lambda p: (DAYS.index(p["day"]), seconds(p["start_time"]), p["name"]))
	period_map = {p["name"]: p for p in periods}
	for p in periods:
		if seconds(p["start_time"]) >= seconds(p["end_time"]):
			raise ValueError("Period must end after it starts")
	blocked = []
	for row in availability:
		p = period_map[row["period"]]
		if row["day"] != p["day"]:
			raise ValueError("Availability day must match its period")
		blocked.append({**p, "instructor": row["instructor"]})
	choices = {}
	limits = {}
	lessons = []
	for req in sorted(requirements, key=lambda r: r["name"]):
		for key in ("lessons_per_week", "max_per_day"):
			if isinstance(req[key], bool) or int(req[key]) != req[key] or req[key] <= 0:
				raise ValueError("Lesson counts must be positive integers")
		limits[req["name"]] = req["max_per_day"]
		choices[req["name"]] = []
		for period in periods:
			if period.get("is_break") or any(overlaps(period, b) for b in periods if b.get("is_break")):
				continue
			if any(b["instructor"] == req["instructor"] and overlaps(period, b) for b in blocked):
				continue
			for room in [req["room"]] if req.get("room") else sorted(rooms):
				choices[req["name"]].append(
					{
						"requirement": req["name"],
						"period": period["name"],
						"day": period["day"],
						"start_time": str(period["start_time"]),
						"end_time": str(period["end_time"]),
						"room": room,
						"instructor": req["instructor"],
						"student_group": req["student_group"],
						"course": req["course"],
					}
				)
		lessons.extend([req["name"]] * req["lessons_per_week"])
	lessons.sort(key=lambda name: (len(choices[name]), name))

	def fits(slot, placed):
		if (
			sum(s["requirement"] == slot["requirement"] and s["day"] == slot["day"] for s in placed)
			>= limits[slot["requirement"]]
		):
			return False
		return not any(
			overlaps(slot, other)
			and any(slot[key] == other[key] for key in ("room", "instructor", "student_group"))
			for other in placed
		)

	best = []
	for name in lessons:
		candidate = next((slot for slot in choices[name] if fits(slot, best)), None)
		if candidate:
			best.append(candidate)
	backtracks = 0
	if len(best) < len(lessons) and max_backtracks:
		placed, selected, indices = [], [], [0]
		depth = 0
		while depth >= 0 and backtracks < max_backtracks:
			if depth == len(lessons):
				if len(placed) > len(best):
					best = placed.copy()
				if len(best) == len(lessons):
					break
				indices[depth] = 1
			options = choices[lessons[depth]] if depth < len(lessons) else []
			if depth == len(lessons) or indices[depth] > len(options):
				indices.pop()
				depth -= 1
				if depth >= 0:
					if selected.pop() is not None:
						placed.pop()
					backtracks += 1
				continue
			index = indices[depth]
			indices[depth] += 1
			slot = options[index] if index < len(options) else None
			if slot is not None and not fits(slot, placed):
				continue
			selected.append(slot)
			if slot is not None:
				placed.append(slot)
				if len(placed) > len(best):
					best = placed.copy()
			depth += 1
			indices.append(0)
	counts = {}
	for slot in best:
		counts[slot["requirement"]] = counts.get(slot["requirement"], 0) + 1
	conflicts = []
	for req in sorted(requirements, key=lambda r: r["name"]):
		for _lesson in range(req["lessons_per_week"] - counts.get(req["name"], 0)):
			conflicts.append(
				{
					"requirement": req["name"],
					"reason": "No feasible period/room within availability, resource and daily limits (search bound {0}).".format(
						max_backtracks
					),
				}
			)
	return {"slots": best, "conflicts": conflicts, "backtracks": backtracks}
