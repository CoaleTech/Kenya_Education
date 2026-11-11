"""Barcode circulation; document controllers reject writes outside these operations."""

from contextlib import contextmanager
from contextvars import ContextVar
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, now_datetime, today

from frappe_education_kenya.parent_ops import linked_students

_OPERATION = ContextVar("library_operation", default=None)
STAFF_READ_ROLES = {"Librarian", "Bursar", "Head Teacher", "Academic Admin", "Instructor"}


@contextmanager
def _operation(action, name=None):
	token = _OPERATION.set((action, name))
	try:
		yield
	finally:
		_OPERATION.reset(token)


def require_operation(doc, actions):
	operation = _OPERATION.get()
	if not operation or operation[0] not in actions or not (operation[1] is doc or operation[1] == doc.name):
		frappe.throw(_("Use the library Issue, Return, Waive or Invoice action."), frappe.PermissionError)
	return operation[0]


def _text(value, label):
	if not isinstance(value, str) or not value.strip() or len(value) > 140:
		frappe.throw(_("Invalid {0}.").format(label))
	return value.strip()


def calculate_fine(due_on, returned_on, daily_rate):
	"""Whole overdue calendar days, rounded once at the currency boundary."""
	try:
		rate = Decimal(str(daily_rate or 0))
	except InvalidOperation:
		frappe.throw(_("Fine per day must be a non-negative number."))
	if not rate.is_finite() or rate < 0:
		frappe.throw(_("Fine per day must be a non-negative number."))
	fine = max(0, date_diff(returned_on, due_on)) * rate
	return float(fine.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _lock(doctype, name):
	if not frappe.db.get_value(doctype, name, "name", for_update=True):
		frappe.throw(_("{0} does not exist.").format(_(doctype)), frappe.DoesNotExistError)


def _copy_for_barcode(barcode):
	name = frappe.db.get_value("Library Copy", {"barcode": barcode}, "name", for_update=True)
	if not name:
		frappe.throw(_("No library copy has this barcode."), frappe.DoesNotExistError)
	copy = frappe.get_doc("Library Copy", name, for_update=True)
	frappe.has_permission("Library Copy", "write", doc=copy, throw=True)
	return copy


def _active_loans(**filters):
	# Locking reads see the latest committed rows after waiting for a borrower/copy lock.
	return frappe.db.get_values(
		"Library Circulation", {"status": "Issued", **filters}, "name", for_update=True, pluck=True
	)


def _result(doc, message):
	return {"ok": True, "name": doc.name, "message": message}


@frappe.whitelist(methods=["POST"])
def issue_copy(barcode: str, borrower_type: str, borrower: str):
	frappe.only_for("Librarian")
	frappe.has_permission("Library Circulation", "create", throw=True)
	barcode, borrower = _text(barcode, _("barcode")), _text(borrower, _("borrower"))
	if borrower_type not in ("Student", "Employee"):
		frappe.throw(_("Borrower type must be Student or Employee."))
	# The borrower row serializes issues of DIFFERENT copies against the same loan limit.
	state_field = "enabled" if borrower_type == "Student" else "status"
	if frappe.db.get_value(borrower_type, borrower, state_field, for_update=True) not in (1, "Active"):
		frappe.throw(_("The borrower must be an active Student or Employee."))
	copy = _copy_for_barcode(barcode)
	if copy.status != "Available" or _active_loans(copy=copy.name):
		frappe.throw(_("This copy is not available."))
	settings = frappe.get_single("Library Settings")
	settings.validate()
	limit = settings.max_loans_student if borrower_type == "Student" else settings.max_loans_staff
	if len(_active_loans(borrower_type=borrower_type, borrower=borrower)) >= cint(limit):
		frappe.throw(_("The borrower has reached the loan limit."))
	currency = frappe.db.get_single_value("Education Kenya Settings", "default_currency")
	if not currency:
		frappe.throw(_("Set the default currency in Education Kenya Settings first."))
	doc = frappe.get_doc(
		{
			"doctype": "Library Circulation",
			"copy": copy.name,
			"borrower_type": borrower_type,
			"borrower": borrower,
			"issued_on": now_datetime(),
			"due_on": add_days(today(), cint(settings.loan_days)),
			"status": "Issued",
			"fine_amount": 0,
			"fine_status": "None",
			"currency": currency,
			"issued_by": frappe.session.user,
		}
	)
	# Naming occurs before validate; tie the capability to this in-memory document, not caller flags.
	with _operation("issue", doc):
		doc.insert()
	with _operation("copy", copy.name):
		copy.status = "Issued"
		copy.save()
	return _result(doc, _("Copy issued."))


@frappe.whitelist(methods=["POST"])
def return_copy(barcode: str):
	frappe.only_for("Librarian")
	frappe.has_permission("Library Circulation", "write", throw=True)
	copy = _copy_for_barcode(_text(barcode, _("barcode")))
	loans = _active_loans(copy=copy.name)
	if copy.status != "Issued" or len(loans) != 1:
		frappe.throw(_("This copy does not have one active loan to return."))
	doc = frappe.get_doc("Library Circulation", loans[0], for_update=True)
	frappe.has_permission("Library Circulation", "write", doc=doc, throw=True)
	with _operation("return", doc.name):
		doc.returned_on = now_datetime()
		doc.fine_amount = calculate_fine(
			doc.due_on, doc.returned_on, frappe.get_single("Library Settings").fine_per_day
		)
		doc.fine_status = "Pending" if doc.fine_amount else "None"
		doc.status = "Returned"
		doc.save()
	with _operation("copy", copy.name):
		copy.status = "Available"
		copy.save()
	return _result(doc, _("Copy returned."))


@frappe.whitelist(methods=["POST"])
def waive_fine(circulation: str, reason: str):
	frappe.only_for("Head Teacher")
	circulation = _text(circulation, _("circulation"))
	if not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
		frappe.throw(_("A waiver reason of up to 1000 characters is required."))
	_lock("Library Circulation", circulation)
	doc = frappe.get_doc("Library Circulation", circulation, for_update=True)
	frappe.has_permission("Library Circulation", "write", doc=doc, throw=True)
	if doc.fine_status != "Pending" or doc.fine_invoice or not doc.fine_amount:
		frappe.throw(_("Only a pending, uninvoiced fine can be waived."))
	with _operation("waive", doc.name):
		doc.fine_status, doc.waiver_reason, doc.waived_by = "Waived", reason.strip(), frappe.session.user
		doc.save()
	return _result(doc, _("Fine waived."))


@frappe.whitelist(methods=["POST"])
def invoice_fine(circulation: str):
	frappe.only_for("Bursar")
	circulation = _text(circulation, _("circulation"))
	_lock("Library Circulation", circulation)
	doc = frappe.get_doc("Library Circulation", circulation, for_update=True)
	frappe.has_permission("Library Circulation", "write", doc=doc, throw=True)
	if doc.borrower_type != "Student":
		frappe.throw(_("Employee fines are record-only and cannot be invoiced."))
	if doc.fine_invoice:
		frappe.has_permission("Sales Invoice", "read", doc=doc.fine_invoice, throw=True)
		return {**_result(doc, _("Fine invoice already exists.")), "invoice": doc.fine_invoice}
	if doc.status != "Returned" or doc.fine_status != "Pending" or doc.fine_amount <= 0:
		frappe.throw(_("Only a pending fine on a returned loan can be invoiced."))
	frappe.has_permission("Sales Invoice", "create", throw=True)
	customer = frappe.db.get_value("Student", doc.borrower, "customer", for_update=True)
	if not customer:
		frappe.throw(_("The student must have a linked Customer before invoicing."))
	settings = frappe.get_single("Education Kenya Settings")
	library_settings = frappe.get_single("Library Settings")
	company, account, cost_center = settings.company, settings.default_fee_account, settings.cost_center
	if not company or not account or not cost_center or not library_settings.fine_item:
		frappe.throw(_("Configure Company, Fee Account, Cost Center and the library Fine Item first."))
	account_doc = frappe.get_doc("Account", account)
	center = frappe.get_doc("Cost Center", cost_center)
	if account_doc.company != company or center.company != company:
		frappe.throw(_("The fine account and cost center must belong to the configured Company."))
	if account_doc.is_group or account_doc.disabled or account_doc.root_type != "Income" or center.is_group:
		frappe.throw(_("Use an enabled income account and a non-group cost center for fines."))
	item = frappe.get_doc("Item", library_settings.fine_item)
	if item.disabled or not item.is_sales_item or item.is_stock_item or item.is_fixed_asset:
		frappe.throw(_("The Fine Item must be an enabled, non-stock sales item."))
	company_currency = frappe.db.get_value("Company", company, "default_currency")
	if doc.currency != settings.default_currency or doc.currency != company_currency:
		frappe.throw(_("The fine currency must match the configured school and Company currency."))
	price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
	if not price_list:
		frappe.throw(_("Set a default Selling Price List in Selling Settings before invoicing fines."))
	invoice = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": customer,
			"company": company,
			"currency": doc.currency,
			"selling_price_list": price_list,
			"conversion_rate": 1,
			"posting_date": today(),
			"due_date": today(),
			"remarks": _("Library fine for {0}").format(doc.name),
			"items": [
				{
					"item_code": item.name,
					"qty": 1,
					"rate": doc.fine_amount,
					"income_account": account,
					"cost_center": cost_center,
				}
			],
		}
	)
	invoice.insert()
	with _operation("invoice", doc.name):
		doc.fine_invoice, doc.fine_status = invoice.name, "Invoiced"
		doc.save()
	return {
		**_result(doc, _("Draft fine invoice created; Bursar submission is required.")),
		"invoice": invoice.name,
	}


def _staff(user):
	return user == "Administrator" or bool(STAFF_READ_ROLES.intersection(frappe.get_roles(user)))


def _student_loan_condition(students):
	values = ", ".join(frappe.db.escape(student) for student in students)
	return (
		"`tabLibrary Circulation`.`borrower_type` = 'Student' "
		f"and `tabLibrary Circulation`.`borrower` in ({values})"
	)


def circulation_query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if _staff(user):
		return ""
	students = linked_students(user)
	return f"({_student_loan_condition(students)})" if students else "1=0"


def circulation_has_permission(doc, ptype=None, user=None, debug=False):
	user = user or frappe.session.user
	if _staff(user):
		return True
	if (ptype or "read") not in {"read", "print", "select"}:
		return False
	return doc.borrower_type == "Student" and doc.borrower in linked_students(user)


def copy_query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if _staff(user):
		return ""
	students = linked_students(user)
	if not students:
		return "1=0"
	return f"""exists (select 1 from `tabLibrary Circulation`
		where `tabLibrary Circulation`.`copy` = `tabLibrary Copy`.`name`
		and {_student_loan_condition(students)})"""


def copy_has_permission(doc, ptype=None, user=None, debug=False):
	user = user or frappe.session.user
	if _staff(user):
		return True
	if (ptype or "read") not in {"read", "print", "select"}:
		return False
	students = linked_students(user)
	return bool(
		students
		and frappe.db.exists(
			"Library Circulation",
			{"copy": doc.name, "borrower_type": "Student", "borrower": ["in", students]},
		)
	)


def setup():
	"""Idempotent catalogue extensions; called by the parent's install/migrate integration."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(
		{
			"Article": [
				{"fieldname": "kenya_isbn", "fieldtype": "Data", "label": "ISBN", "insert_after": "author"},
				{
					"fieldname": "kenya_call_number",
					"fieldtype": "Data",
					"label": "Call Number",
					"insert_after": "kenya_isbn",
				},
				{
					"fieldname": "kenya_publisher",
					"fieldtype": "Data",
					"label": "Publisher",
					"insert_after": "kenya_call_number",
				},
				{
					"fieldname": "kenya_edition",
					"fieldtype": "Data",
					"label": "Edition",
					"insert_after": "kenya_publisher",
				},
			]
		}
	)
