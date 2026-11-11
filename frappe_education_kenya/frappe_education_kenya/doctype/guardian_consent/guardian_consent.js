frappe.ui.form.on("Guardian Consent", {
	refresh(frm) {
		if (!frm.is_new()) frm.disable_form();
	},
	onload(frm) {
		if (frm.is_new() && !frm.doc.captured_via) frm.set_value("captured_via", "Portal");
	},
});
