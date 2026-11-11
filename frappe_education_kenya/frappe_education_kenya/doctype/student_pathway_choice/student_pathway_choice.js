frappe.ui.form.on("Student Pathway Choice", {
	setup(frm) {
		for (const field of ["first_choice", "second_choice", "placement"]) {
			frm.set_query(field, () => ({ filters: { enabled: 1 } }));
		}
	},
	refresh(frm) {
		const state = frm.doc.workflow_state || "Draft";
		for (const field of ["student", "academic_year", "first_choice", "second_choice", "rationale"]) {
			frm.set_df_property(field, "read_only", state !== "Draft");
		}
		frm.set_df_property("placement", "read_only", !["Approved", "Rejected"].includes(state));
		frm.set_df_property("override_reason", "read_only", !["Approved", "Rejected"].includes(state));
		if (state === "Draft" && !frm.doc.guardian_consent) {
			frm.set_intro(__("A linked guardian must grant Data Sharing consent before Submit Choice."), "orange");
		}
		if (frm.is_new() && !frm.doc.academic_year) {
			frappe.call({
				method: "frappe_education_kenya.pathways.get_current_academic_year",
				type: "GET",
			}).then(({ message }) => {
				if (message?.academic_year && !frm.doc.academic_year) {
					frm.set_value("academic_year", message.academic_year);
				}
			});
		}
	},
});
