"""Server-side logic for MoE Return Submission: scheduled generation and deadline checks."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, today


class MoEReturnSubmission(Document):
	def validate(self):
		if self.template and not self.template_name:
			template = frappe.get_cached_doc("MoE Return Template", self.template)
			self.template_name = template.template_name
			self.return_type = template.return_type


def check_upcoming_deadlines():
	"""Daily scheduled task: notify responsible roles about approaching MoE deadlines.

	Looks at open (non-terminal) submissions whose due_date is within the
	template's configured reminder window and nudges the responsible role
	via a system notification log entry.
	"""
	open_submissions = frappe.get_all(
		"MoE Return Submission",
		filters={"submission_status": ["in", ["Draft", "Validating", "Ready for Review"]]},
		fields=["name", "template", "due_date", "template_name"],
	)

	for submission in open_submissions:
		if not submission.due_date:
			continue

		reminder_days = (
			frappe.db.get_value("MoE Return Template", submission.template, "reminder_days_before") or 0
		)
		reminder_start = add_days(getdate(submission.due_date), -int(reminder_days))

		if getdate(today()) >= reminder_start:
			frappe.db.set_value(
				"MoE Return Submission",
				submission.name,
				"submission_status",
				"Overdue"
				if getdate(today()) > getdate(submission.due_date)
				else submission.get("submission_status"),
				update_modified=False,
			)
			responsible_role = frappe.db.get_value(
				"MoE Return Template", submission.template, "responsible_role"
			)
			if responsible_role:
				users = frappe.get_all(
					"Has Role", filters={"role": responsible_role, "parenttype": "User"}, fields=["parent"]
				)
				for u in users:
					frappe.publish_realtime(
						event="moe_deadline_reminder",
						message={
							"submission": submission.name,
							"template": submission.template_name,
							"due_date": str(submission.due_date),
						},
						user=u.parent,
					)


def generate_daily_attendance_snapshot():
	"""Daily scheduled task: aggregate a rolling attendance snapshot for MoE reporting.

	This is a lightweight placeholder aggregation — it stores nothing durable
	beyond a log entry, since Frappe Education's Student Attendance DocType
	already retains the source-of-truth records that EMIS-008 reports read.
	"""
	count = frappe.db.count("Student Attendance", filters={"date": today()})
	frappe.logger().info(f"Daily attendance records captured for {today()}: {count}")


def auto_generate_monthly_enrolment_return():
	"""Monthly scheduled task: draft a new MoE Return Submission for enrolment (EMIS-001)."""
	template_name = "EMIS-001"
	if not frappe.db.exists("MoE Return Template", template_name):
		return

	reporting_period = frappe.utils.formatdate(today(), "MMMM yyyy")
	existing = frappe.db.exists(
		"MoE Return Submission",
		{"template": template_name, "reporting_period": reporting_period},
	)
	if existing:
		return

	submission = frappe.new_doc("MoE Return Submission")
	submission.template = template_name
	submission.reporting_period = reporting_period
	submission.submission_status = "Draft"
	submission.insert(ignore_permissions=True)
	frappe.db.commit()
