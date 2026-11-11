frappe.ui.form.on("Timetable Availability", {
	setup(frm) {
		frm.set_query("period", () => ({ filters: frm.doc.day ? { day: frm.doc.day } : {} }));
	},
	period(frm) {
		if (frm.doc.period) frappe.db.get_value("Timetable Period", frm.doc.period, "day").then((r) => {
			if (r.message) frm.set_value("day", r.message.day);
		});
	},
});
