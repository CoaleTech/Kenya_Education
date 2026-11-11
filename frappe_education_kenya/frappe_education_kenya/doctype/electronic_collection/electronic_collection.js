frappe.ui.form.on("Electronic Collection", {
	refresh(frm) {
		if (frm.is_new() || !frappe.user.has_role("Bursar")) return;
		if (["New", "Needs Review", "Matched"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Match Exact Student ID"), () => frm.call({ method: "frappe_education_kenya.collections.match", args: { name: frm.doc.name }, freeze: true }).then(() => frm.reload_doc()));
			frm.add_custom_button(__("Reject"), () => frappe.prompt({ fieldname: "reason", label: __("Reason"), fieldtype: "Small Text", reqd: 1 }, (v) => frappe.call({ method: "frappe_education_kenya.collections.reject", args: { name: frm.doc.name, reason: v.reason } }).then(() => frm.reload_doc())));
		}
		if (frm.doc.status === "Matched") frm.add_custom_button(__("Approve and Post Payment"), () => frappe.confirm(__("Approve this collection and submit its Payment Entry to the ledger?"), () => frappe.call({ method: "frappe_education_kenya.collections.approve", args: { name: frm.doc.name }, freeze: true }).then(() => frm.reload_doc())));
	},
});
