frappe.listview_settings["Exam Paper"] = {
	add_fields: ["workflow_state", "instructor"],
	get_indicator(doc) {
		const colors = {"Draft": "gray", "Submitted": "orange", "In Review": "orange", "Returned": "red", "Approved": "green", "Locked": "blue", "Released": "green"};
		return [__(doc.workflow_state), colors[doc.workflow_state] || "gray", "workflow_state,=," + doc.workflow_state];
	},
};
