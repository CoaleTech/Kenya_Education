frappe.listview_settings["Student Pathway Choice"] = {
	add_fields: ["workflow_state", "student", "academic_year"],
	get_indicator(doc) {
		const colors = { Draft: "gray", Submitted: "orange", Approved: "blue", Rejected: "red", Placed: "green" };
		return [__(doc.workflow_state), colors[doc.workflow_state] || "gray", "workflow_state,=," + doc.workflow_state];
	},
};
