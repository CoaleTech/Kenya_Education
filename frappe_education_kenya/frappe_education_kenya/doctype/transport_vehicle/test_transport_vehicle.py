"""Tests for Transport Vehicle NTSA compliance monitoring."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from frappe_education_kenya.frappe_education_kenya.doctype.transport_vehicle.transport_vehicle import (
	check_vehicle_compliance,
)


class TestTransportVehicleCompliance(FrappeTestCase):
	def _make_vehicle(self, reg, insurance_expiry=None, ntsa_expiry=None, status="Active"):
		doc = frappe.new_doc("Transport Vehicle")
		doc.vehicle_registration = reg
		doc.vehicle_type = "School Bus"
		doc.seating_capacity = 33
		doc.vehicle_status = status
		if insurance_expiry:
			doc.insurance_expiry = insurance_expiry
		if ntsa_expiry:
			doc.ntsa_inspection_expiry = ntsa_expiry
		doc.insert(ignore_permissions=True)
		return doc

	def test_expired_and_expiring_vehicles_logged_without_raising(self):
		frappe.db.delete("Error Log")

		self._make_vehicle(
			"KKX-EXPIRED-001",
			insurance_expiry=add_days(today(), -5),
			ntsa_expiry=add_days(today(), 100),
		)
		self._make_vehicle(
			"KKX-EXPIRING-002",
			insurance_expiry=add_days(today(), 10),
			ntsa_expiry=add_days(today(), 100),
		)
		self._make_vehicle(
			"KKX-SAFE-003",
			insurance_expiry=add_days(today(), 200),
			ntsa_expiry=add_days(today(), 200),
		)

		# Should not raise
		check_vehicle_compliance()

		errors = frappe.get_all(
			"Error Log", filters={"method": ["like", "%Transport vehicle compliance%"]}
		)
		self.assertGreaterEqual(len(errors), 1)

	def test_no_vehicles_no_error(self):
		frappe.db.delete("Transport Vehicle")
		frappe.db.delete("Error Log")
		check_vehicle_compliance()
		errors = frappe.get_all(
			"Error Log", filters={"method": ["like", "%Transport vehicle compliance%"]}
		)
		self.assertEqual(len(errors), 0)

	def tearDown(self):
		frappe.db.rollback()
