frappe.ui.form.on("Library Copy", {
	refresh(frm) {
		if (frm.is_new() || !frappe.user.has_role("Librarian")) return;
		if (frm.doc.status === "Available") {
			frm.add_custom_button(__("Issue Copy"), () => frappe.prompt([
				{ fieldname: "borrower_type", fieldtype: "Select", label: __("Borrower Type"), options: "Student\nEmployee", default: "Student", reqd: 1 },
				{ fieldname: "borrower", fieldtype: "Dynamic Link", label: __("Borrower"), options: "borrower_type", reqd: 1 },
			], (values) => frappe.call({
				method: "frappe_education_kenya.library.issue_copy",
				args: { barcode: frm.doc.barcode, ...values }, freeze: true,
				callback: (r) => { if (r.message?.ok) frappe.set_route("Form", "Library Circulation", r.message.name); },
			}), __("Issue Copy"), __("Issue")));
		}
		if (frm.doc.status === "Issued") {
			frm.add_custom_button(__("Return Copy"), () => frappe.confirm(__("Return this copy and calculate any overdue fine?"), () => frappe.call({
				method: "frappe_education_kenya.library.return_copy", args: { barcode: frm.doc.barcode }, freeze: true,
				callback: (r) => { if (r.message?.ok) frappe.set_route("Form", "Library Circulation", r.message.name); },
			})));
		}
	},
});
