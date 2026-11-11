frappe.ui.form.on("Transport Subscription", {
	refresh(frm) {
		if (frm.doc.sales_invoice) {
			frm.add_custom_button(__("View Invoice"), () =>
				frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice)
			);
		} else if (!frm.is_new() && frappe.user.has_role("Bursar") && frm.doc.subscription_status === "Active") {
			frm.add_custom_button(__("Create Draft Invoice"), () => {
				if (frm.is_dirty()) {
					frappe.msgprint(__("Save the subscription before creating an invoice."));
					return;
				}
				frappe.confirm(__("Create a draft invoice for the selected net fare?"), () => {
					frappe.call({
						method: "frappe_education_kenya.transport.create_invoice",
						args: { subscription: frm.doc.name },
						freeze: true,
						callback(r) {
							if (r.message) {
								frm.reload_doc();
								frappe.set_route("Form", "Sales Invoice", r.message.name);
							}
						},
					});
				});
			});
		}
	},
	route: lookup_transport_fare,
	trip_type: lookup_transport_fare,
	start_date: lookup_transport_fare,
});

function lookup_transport_fare(frm) {
	const { route, trip_type, start_date } = frm.doc;
	if (!route || !trip_type || !start_date || frm.doc.sales_invoice) return;
	frappe.call({
		method: "frappe_education_kenya.transport.get_fare",
		args: { route, trip_type, start_date },
		callback(r) {
			if (r.message && frm.doc.route === route && frm.doc.trip_type === trip_type && frm.doc.start_date === start_date) {
				frm.set_value("fee_amount", r.message.fee_amount);
			}
		},
	});
}
