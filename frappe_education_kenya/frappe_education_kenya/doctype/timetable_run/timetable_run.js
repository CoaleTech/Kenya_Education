frappe.ui.form.on("Timetable Run", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Conflicts"), () => {
			frappe.set_route("query-report", "Timetable Conflicts", { run: frm.doc.name });
		});
		frm.add_custom_button(__("Print Class / Teacher"), () => {
			frappe.prompt([
				{ fieldname: "student_group", label: __("Student Group"), fieldtype: "Link", options: "Student Group" },
				{ fieldname: "instructor", label: __("Instructor"), fieldtype: "Link", options: "Instructor" },
			], (values) => {
				const query = new URLSearchParams({ doctype: "Timetable Run", name: frm.doc.name,
					format: "Timetable", no_letterhead: "1", student_group: values.student_group || "",
					instructor: values.instructor || "" });
				window.open(`/printview?${query.toString()}`, "_blank", "noopener");
			}, __("Print Timetable"), __("Print"));
		});
		if (!frappe.user.has_role("Academic Admin")) return;
		if (frm.doc.status !== "Published") {
			frm.add_custom_button(__("Generate"), () => {
				frappe.call({ method: "frappe_education_kenya.timetable.generate", type: "POST",
					args: { run: frm.doc.name }, freeze: true,
					callback(r) { if (r.message) frappe.msgprint(r.message.message); },
				});
			});
		}
		if (frm.doc.status === "Generated" && !(frm.doc.conflicts || []).length) {
			frm.add_custom_button(__("Publish"), () => {
				frappe.confirm(__("Replace prior unlinked timetable schedules for this term?"), () => {
					frappe.call({ method: "frappe_education_kenya.timetable.publish", type: "POST",
						args: { run: frm.doc.name }, freeze: true,
						callback(r) { if (r.message) { frappe.msgprint(r.message.message); frm.reload_doc(); } },
					});
				});
			});
		}
	},
});
