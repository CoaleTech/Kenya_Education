"""Server-side logic for Transport Vehicle: NTSA compliance monitoring."""

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, today


class TransportVehicle(Document):
	pass


def check_vehicle_compliance():
	"""Weekly cron (Mondays 08:00): flag vehicles with expiring insurance/inspection.

	Notifies Transport Managers about any Active vehicle whose insurance or
	NTSA inspection certificate expires within the next 30 days, and marks
	already-expired vehicles for Maintenance follow-up.
	"""
	warning_window = add_days(getdate(today()), 30)

	vehicles = frappe.get_all(
		"Transport Vehicle",
		filters={"vehicle_status": "Active"},
		fields=["name", "vehicle_registration", "insurance_expiry", "ntsa_inspection_expiry"],
	)

	expiring, expired = [], []
	for vehicle in vehicles:
		for field, label in (("insurance_expiry", "insurance"), ("ntsa_inspection_expiry", "NTSA inspection")):
			expiry = vehicle.get(field)
			if not expiry:
				continue
			expiry_date = getdate(expiry)
			if expiry_date < getdate(today()):
				expired.append((vehicle.vehicle_registration, label, expiry_date))
			elif expiry_date <= warning_window:
				expiring.append((vehicle.vehicle_registration, label, expiry_date))

	if expiring or expired:
		lines = []
		for reg, label, date in expired:
			lines.append(f"EXPIRED: {reg} — {label} expired {date}")
		for reg, label, date in expiring:
			lines.append(f"Expiring soon: {reg} — {label} expires {date}")

		frappe.log_error(
			title="Transport vehicle compliance alerts",
			message="\n".join(lines),
		)
