frappe.ui.form.on("Lesson Plan", {
	setup(frm) {
		frm.set_query("scheme_of_work", () => ({filters: {workflow_state: "Approved", instructor: frm.doc.instructor, course: frm.doc.course}}));
	},
	refresh(frm) {
		if (["Draft", "Returned"].includes(frm.doc.workflow_state) && frm.doc.scheme_of_work) {
			frm.add_custom_button(__("Choose Scheme Week"), () => choose_scheme_week(frm));
		}
	},
	async scheme_of_work(frm) {
		await frm.set_value("scheme_week", "");
		if (frm.doc.scheme_of_work) await choose_scheme_week(frm);
	},
	async instructor(frm) {
		await frm.set_value("scheme_of_work", "");
		await frm.set_value("scheme_week", "");
	},
	async course(frm) {
		await frm.set_value("scheme_of_work", "");
		await frm.set_value("scheme_week", "");
	},
});

async function choose_scheme_week(frm) {
	const response = await frappe.call({method: "frappe_education_kenya.teaching.scheme_weeks", type: "GET", args: {scheme: frm.doc.scheme_of_work}});
	const weeks = response.message || [];
	if (!weeks.length) return frappe.msgprint(__("The approved scheme has no weeks."));
	const labels = weeks.map((week) => `${week.week_no}: ${week.topic}`);
	frappe.prompt([{fieldname: "week", fieldtype: "Select", label: __("Scheme Week"), options: labels.join("\n"), reqd: 1}],
		(values) => frm.set_value("scheme_week", weeks[labels.indexOf(values.week)].name), __("Choose Scheme Week"), __("Select"));
}
