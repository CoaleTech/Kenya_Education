frappe.listview_settings["Bursary Award"] = {
	add_fields: ["workflow_state"],
	get_indicator(doc) {
		const state = doc.workflow_state;
		const color = ["Met", "Posted", "Approved", "Allocated"].includes(state) ? "green" : ["Rejected", "Broken", "Cancelled"].includes(state) ? "red" : "orange";
		return [__(state), color, "workflow_state,=," + state];
	},
};
