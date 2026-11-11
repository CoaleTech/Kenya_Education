frappe.ui.form.on("Fee Pledge", {
	refresh(frm) {
		if (frm.is_new() || !frappe.user.has_role("Bursar") || ["Met", "Cancelled"].includes(frm.doc.status)) return;
		// Standard Payment Entry form; the Fee Pledge link drives the met-amount rollup on submit.
		frm.add_custom_button(__("Record Payment"), () =>
			frappe.new_doc("Payment Entry", { payment_type: "Receive", party_type: "Student", party: frm.doc.student, fee_pledge: frm.doc.name })
		);
	},
});
