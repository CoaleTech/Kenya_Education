frappe.query_reports["Overdue Library Items"] = {
	filters: [
		{ fieldname: "as_of", label: __("As Of"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "borrower_type", label: __("Borrower Type"), fieldtype: "Select", options: "\nStudent\nEmployee" },
		{ fieldname: "borrower", label: __("Borrower"), fieldtype: "Dynamic Link", options: "borrower_type" },
		{ fieldname: "include_returned_with_fines", label: __("Include Returned Copies with Recorded Fines"), fieldtype: "Check", default: 0 },
	],
};
