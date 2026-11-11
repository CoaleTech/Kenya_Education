frappe.query_reports["Pathway Placement by Combination"] = {
	filters: [
		{ fieldname: "academic_year", label: __("Academic Year"), fieldtype: "Link", options: "Academic Year" },
		{ fieldname: "pathway", label: __("Pathway"), fieldtype: "Link", options: "CBC Pathway" },
		{ fieldname: "track", label: __("Track"), fieldtype: "Data" },
		{ fieldname: "combination", label: __("Combination"), fieldtype: "Link", options: "CBC Subject Combination" },
	],
};
