frappe.query_reports["Guardian Consent Coverage"] = {
	filters: [
		{fieldname: "guardian", label: __("Guardian"), fieldtype: "Link", options: "Guardian"},
		{fieldname: "student", label: __("Student"), fieldtype: "Link", options: "Student"},
		{fieldname: "purpose", label: __("Purpose"), fieldtype: "Select", options: "\nMessaging\nPhoto\nTrip\nData Sharing"},
		{fieldname: "status", label: __("Latest decision"), fieldtype: "Select", options: "\nGranted\nRevoked\nMissing"},
	],
};
