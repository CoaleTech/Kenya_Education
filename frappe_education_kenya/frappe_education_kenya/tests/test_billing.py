"""Day Scholar / Boarder billing: category guards and the Fee Structure -> Fee Schedule -> Sales Invoice route."""

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from education.education.doctype.fee_schedule.fee_schedule import generate_fees, get_fee_structure
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from frappe_education_kenya import transport
from frappe_education_kenya.billing import validate_kenya_fee_structure
from frappe_education_kenya.install import seed_student_categories

COMPANY = "_Test Company"
CURRENT_YEAR = "EDK-BILL-CURRENT"
PAST_YEAR = "EDK-BILL-PAST"
PROGRAM = "EDK Bill Program"
BOARDER_FEES = (("EDK Bill Tuition", 5000), ("EDK Bill Boarding", 3000))


def make_student(key, boarder_status=None):
	return frappe.get_doc(
		{
			"doctype": "Student",
			"first_name": "Bill",
			"last_name": key,
			"student_email_id": f"edk.billing.{key}@example.com",
			"kenya_boarder_status": boarder_status,
		}
	).insert(ignore_permissions=True)


def make_enrollment(student, academic_year, student_category=None, submit=False):
	doc = frappe.get_doc(
		{
			"doctype": "Program Enrollment",
			"student": student.name,
			"program": PROGRAM,
			"academic_year": academic_year,
			"academic_term": f"{academic_year} (Term 1)",
			"enrollment_date": nowdate(),
			"student_category": student_category,
		}
	).insert(ignore_permissions=True)
	if submit:
		doc.submit()
	return doc


def make_structure(category):
	doc = frappe.get_doc(
		{
			"doctype": "Fee Structure",
			"program": PROGRAM,
			"student_category": category,
			"academic_year": CURRENT_YEAR,
			"academic_term": f"{CURRENT_YEAR} (Term 1)",
			"company": COMPANY,
			"components": [{"fees_category": name, "amount": amount} for name, amount in BOARDER_FEES],
		}
	)
	if category is None:
		return doc
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc


class TestBilling(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		frappe.set_user("Administrator")
		seed_student_categories()
		# Fee Category creates a service Item; a bare site has no default UOM for it.
		frappe.db.set_default("stock_uom", "Nos")
		for name, start, end in (
			(CURRENT_YEAR, add_days(nowdate(), -30), add_days(nowdate(), 300)),
			(PAST_YEAR, "2001-01-01", "2001-12-31"),
		):
			frappe.get_doc(
				{
					"doctype": "Academic Year",
					"academic_year_name": name,
					"year_start_date": start,
					"year_end_date": end,
				}
			).insert(ignore_permissions=True)
			frappe.get_doc(
				{
					"doctype": "Academic Term",
					"academic_year": name,
					"term_name": "Term 1",
					"term_start_date": start,
					"term_end_date": end,
				}
			).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Program", "program_name": PROGRAM}).insert(ignore_permissions=True)
		for name, _amount in BOARDER_FEES:
			frappe.get_doc({"doctype": "Fee Category", "category_name": name}).insert(ignore_permissions=True)
		# Sales Invoices need a selling price list; a bare site has none.
		frappe.get_doc(
			{"doctype": "Price List", "price_list_name": "EDK Bill Selling", "selling": 1, "currency": "INR"}
		).insert(ignore_permissions=True)
		frappe.db.set_single_value("Selling Settings", "selling_price_list", "EDK Bill Selling")

	def tearDown(self):
		frappe.db.rollback()

	def test_blank_enrollment_category_takes_boarder_status(self):
		student = make_student("a", "Quarter Boarder")
		self.assertEqual(make_enrollment(student, CURRENT_YEAR).student_category, "Quarter Boarder")

	def test_explicit_enrollment_category_is_kept(self):
		student = make_student("a", "Boarder")
		self.assertEqual(
			make_enrollment(student, CURRENT_YEAR, "Day Scholar").student_category, "Day Scholar"
		)

	def test_current_year_enrollment_needs_a_category(self):
		student = make_student("a")
		with self.assertRaises(frappe.ValidationError):
			make_enrollment(student, CURRENT_YEAR)

	def test_past_year_enrollment_may_stay_blank(self):
		student = make_student("a")
		self.assertFalse(make_enrollment(student, PAST_YEAR).student_category)

	def test_fee_structure_without_category_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			make_structure(None).insert(ignore_permissions=True)

	def test_fee_schedule_category_must_match_structure(self):
		structure = make_structure("Boarder")
		for category in ("Day Scholar", None):
			schedule = get_fee_structure(structure.name)
			schedule.student_category = category
			schedule.due_date = add_days(nowdate(), 2)
			with self.subTest(category=category), self.assertRaises(frappe.ValidationError):
				schedule.insert(ignore_permissions=True)

	def test_boarder_cannot_have_active_transport_subscription(self):
		boarder = make_student("b", "Boarder")
		quarter = make_student("q", "Quarter Boarder")

		def subscription(student, status="Active"):
			doc = frappe._dict(
				student=student.name,
				route="ROUTE-1",
				trip_type="Two Way",
				start_date="2026-03-01",
				discount_type="None",
				discount_value=0,
				discount_reason="",
				discount_approved_by=None,
				sales_invoice=None,
				subscription_status=status,
			)
			doc.get_doc_before_save = lambda: None
			doc.precision = lambda field: 2
			return doc

		with self.assertRaises(frappe.ValidationError):
			transport.validate_subscription(subscription(boarder))
		fares = [frappe._dict(trip_type="Two Way", amount=9000, effective_from="2026-01-01")]
		with patch.object(frappe, "get_doc", return_value=SimpleNamespace(fares=fares)):
			transport.validate_subscription(subscription(boarder, "Suspended"))
			quarter_doc = subscription(quarter)
			transport.validate_subscription(quarter_doc)
		self.assertEqual(quarter_doc.fee_amount, 9000)

	def test_boarder_schedule_bills_only_the_boarder(self):
		day = make_student("day", "Day Scholar")
		boarder = make_student("boarder", "Boarder")
		for student in (day, boarder):
			make_enrollment(student, CURRENT_YEAR, submit=True)
		group = frappe.get_doc(
			{
				"doctype": "Student Group",
				"student_group_name": "EDK Bill Group",
				"academic_year": CURRENT_YEAR,
				"academic_term": f"{CURRENT_YEAR} (Term 1)",
				"group_based_on": "Batch",
				"program": PROGRAM,
				"students": [{"student": student.name} for student in (day, boarder)],
			}
		).insert(ignore_permissions=True)
		make_structure("Day Scholar")
		structure = make_structure("Boarder")
		schedule = get_fee_structure(structure.name)
		schedule.due_date = add_days(nowdate(), 2)
		schedule.append("student_groups", {"student_group": group.name})
		schedule.insert(ignore_permissions=True)
		schedule.submit()

		generate_fees(schedule.name)

		status, error = frappe.db.get_value("Fee Schedule", schedule.name, ["status", "error_log"])
		self.assertEqual(status, "Invoice Created", error)
		invoices = frappe.get_all(
			"Sales Invoice", filters={"fee_schedule": schedule.name}, fields=["student", "grand_total"]
		)
		self.assertEqual(len(invoices), 1)
		self.assertEqual(invoices[0].student, boarder.name)
		self.assertEqual(invoices[0].grand_total, structure.total_amount)
		self.assertEqual(structure.total_amount, sum(amount for _name, amount in BOARDER_FEES))


class FakeStructure(dict):
	get = dict.get


class TestFeeStructureRule(FrappeTestCase):
	def test_missing_student_category_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			validate_kenya_fee_structure(FakeStructure(kenya_fee_category="Tuition Fee"))

	def test_category_without_transport_components_is_accepted(self):
		validate_kenya_fee_structure(FakeStructure(student_category="Day Scholar"))

	def test_government_regulated_without_cbc_level_only_warns(self):
		validate_kenya_fee_structure(
			FakeStructure(student_category="Boarder", kenya_is_government_regulated=1, kenya_cbc_level=None)
		)
