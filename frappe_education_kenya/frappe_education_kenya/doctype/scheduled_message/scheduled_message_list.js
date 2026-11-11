frappe.listview_settings["Scheduled Message"] = {
	add_fields: ["status", "audience", "send_at"],
	get_indicator(doc) {
		const colors = {Draft: "gray", Scheduled: "blue", Sending: "orange", Sent: "blue", Failed: "red"};
		return [__(doc.status), colors[doc.status] || "gray", "status,=," + doc.status];
	},
};
