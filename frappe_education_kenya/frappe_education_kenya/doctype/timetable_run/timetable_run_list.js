frappe.listview_settings["Timetable Run"] = {
	add_fields: ["status", "academic_term"],
	get_indicator(doc) {
		const colors = { Draft: "gray", Generated: "blue", Published: "green", Failed: "red" };
		return [__(doc.status), colors[doc.status], `status,=,${doc.status}`];
	},
};
