frappe.listview_settings["Guardian Consent"] = {
	add_fields: ["status", "purpose", "guardian", "student"],
	get_indicator(doc) {
		return [__(doc.status), doc.status === "Granted" ? "blue" : "red", "status,=," + doc.status];
	},
};
