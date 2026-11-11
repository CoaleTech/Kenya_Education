frappe.ui.form.on("Transport Route", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Subscriptions"), () => {
			frappe.route_options = { route: frm.doc.name };
			frappe.set_route("List", "Transport Subscription");
		});
		if (!frappe.model.can_read("Transport Subscription")) return;
		frappe.call({
			method: "frappe_education_kenya.transport.route_summary",
			args: { route: frm.doc.name },
			callback(r) {
				if (!r.message) return;
				// Display fresh totals without dirtying the form or saving on open.
				Object.assign(frm.doc, r.message);
				frm.refresh_field("total_subscribers");
				frm.refresh_field("monthly_revenue");
			},
		});
	},
});
