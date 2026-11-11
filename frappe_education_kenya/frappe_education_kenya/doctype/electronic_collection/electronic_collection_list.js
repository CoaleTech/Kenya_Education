frappe.listview_settings["Electronic Collection"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const state = doc.status;
		const color = ["Met", "Posted", "Approved", "Allocated"].includes(state) ? "green" : ["Rejected", "Broken", "Cancelled"].includes(state) ? "red" : "orange";
		return [__(state), color, "status,=," + state];
	},
};
