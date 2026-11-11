frappe.ui.form.on("Library Circulation", {
	refresh(frm) {
		if (frm.is_new()) {
			frm.disable_save();
			frm.set_intro(__("Issue or return copies by barcode from the Library Circulation list or a Library Copy."));
			return;
		}
		frm.disable_save();
		if (frm.doc.status === "Issued" && frappe.user.has_role("Librarian")) {
			frm.add_custom_button(__("Return Copy"), () => frappe.confirm(__("Return this copy and calculate any overdue fine?"), () => frappe.db.get_value("Library Copy", frm.doc.copy, "barcode").then((r) => frappe.call({
				method: "frappe_education_kenya.library.return_copy", args: { barcode: r.message.barcode }, freeze: true,
				callback: () => frm.reload_doc(),
			}))));
		}
		if (frm.doc.fine_status !== "Pending") return;
		if (frappe.user.has_role("Head Teacher")) {
			frm.add_custom_button(__("Waive Fine"), () => frappe.prompt({
				fieldname: "reason", fieldtype: "Small Text", label: __("Waiver Reason"), reqd: 1,
			}, ({ reason }) => frappe.call({
				method: "frappe_education_kenya.library.waive_fine", args: { circulation: frm.doc.name, reason }, freeze: true,
				callback: () => frm.reload_doc(),
			}), __("Waive Fine"), __("Waive")));
		}
		if (frm.doc.borrower_type === "Student" && frappe.user.has_role("Bursar")) {
			frm.add_custom_button(__("Create Draft Fine Invoice"), () => frappe.confirm(__("Create a draft invoice for the student's linked Customer? This does not post to the ledger."), () => frappe.call({
				method: "frappe_education_kenya.library.invoice_fine", args: { circulation: frm.doc.name }, freeze: true,
				callback: (r) => { if (r.message?.invoice) frappe.set_route("Form", "Sales Invoice", r.message.invoice); },
			})));
		}
	},
});
