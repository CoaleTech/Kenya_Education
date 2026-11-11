frappe.listview_settings["Library Circulation"] = {
	add_fields: ["status", "due_on"],
	onload(listview) {
		if (!frappe.user.has_role("Librarian")) return;
		listview.page.add_inner_button(__("Issue by Barcode"), () => frappe.prompt([
			{ fieldname: "barcode", fieldtype: "Data", label: __("Scan Barcode"), reqd: 1 },
			{ fieldname: "borrower_type", fieldtype: "Select", label: __("Borrower Type"), options: "Student\nEmployee", default: "Student", reqd: 1 },
			{ fieldname: "borrower", fieldtype: "Dynamic Link", label: __("Borrower"), options: "borrower_type", reqd: 1 },
		], (args) => frappe.call({
			method: "frappe_education_kenya.library.issue_copy", args, freeze: true,
			callback: (r) => { if (r.message?.ok) frappe.set_route("Form", "Library Circulation", r.message.name); },
		}), __("Issue Copy"), __("Issue")));
		listview.page.add_inner_button(__("Return by Barcode"), () => frappe.prompt({
			fieldname: "barcode", fieldtype: "Data", label: __("Scan Barcode"), reqd: 1,
		}, (args) => frappe.call({
			method: "frappe_education_kenya.library.return_copy", args, freeze: true,
			callback: (r) => { if (r.message?.ok) frappe.set_route("Form", "Library Circulation", r.message.name); },
		}), __("Return Copy"), __("Return")));
		listview.page.add_inner_button(__("Overdue Library Items"), () => frappe.set_route("query-report", "Overdue Library Items"));
	},
	get_indicator(doc) {
		if (doc.status === "Issued" && doc.due_on < frappe.datetime.get_today()) return [__("Overdue"), "red", "status,=,Issued|due_on,<," + frappe.datetime.get_today()];
		return [__(doc.status), doc.status === "Returned" ? "green" : "orange", "status,=," + doc.status];
	},
};
