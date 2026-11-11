frappe.listview_settings["Library Copy"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const colors = { Available: "green", Issued: "orange", Lost: "red", Withdrawn: "gray" };
		return [__(doc.status), colors[doc.status], "status,=," + doc.status];
	},
};
