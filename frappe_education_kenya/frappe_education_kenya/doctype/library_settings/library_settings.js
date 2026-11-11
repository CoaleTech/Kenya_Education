frappe.ui.form.on("Library Settings", {
	setup(frm) {
		frm.set_query("fine_item", () => ({ filters: { disabled: 0, is_sales_item: 1, is_stock_item: 0, is_fixed_asset: 0 } }));
	},
	refresh(frm) {
		frm.set_intro(__("Loan limits apply per borrower. Fines accrue by overdue calendar day on return. Employee fines are record-only; only the Bursar can create a student's draft invoice."));
	},
});
