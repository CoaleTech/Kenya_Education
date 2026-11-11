frappe.query_reports["Timetable Conflicts"] = {
	filters: [
		{ fieldname: "run", label: __("Run"), fieldtype: "Link", options: "Timetable Run" },
		{ fieldname: "academic_term", label: __("Academic Term"), fieldtype: "Link", options: "Academic Term" },
	],
};
