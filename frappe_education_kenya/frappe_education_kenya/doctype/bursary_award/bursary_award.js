frappe.ui.form.on("Bursary Award", {
	refresh(frm) {
		if (!frm.is_new() && ["Approved", "Allocated"].includes(frm.doc.workflow_state) && frappe.user.has_role("Bursar")) {
			frm.add_custom_button(__("Allocate Bursary"), () => {
				frappe.prompt([
					{ fieldname: "reference_doctype", label: __("Target Type"), fieldtype: "Select", options: "Sales Invoice\nFees", default: "Sales Invoice", reqd: 1 },
					{ fieldname: "fees", label: __("Fees or Sales Invoice"), fieldtype: "Dynamic Link", options: "reference_doctype", reqd: 1, get_query: () => ({ filters: { docstatus: 1, outstanding_amount: [">", 0] } }) },
					{ fieldname: "amount", label: __("Amount"), fieldtype: "Currency", reqd: 1 },
				], (values) => frappe.call({ method: "frappe_education_kenya.bursary.allocate", args: { award: frm.doc.name, ...values }, freeze: true }).then((r) => { frm.reload_doc(); frappe.set_route("Form", "Payment Entry", r.message.name); }), __("Allocate Bursary"), __("Create Draft Payment"));
			});
		}
	},
});
