frappe.ui.form.on("Scheduled Message", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.status === "Draft" && frappe.model.can_write("Scheduled Message")) {
			frm.add_custom_button(__("Schedule Message"), () => {
				if (frm.is_dirty()) {
					frappe.msgprint(__("Save your changes before scheduling."));
					return;
				}
				frappe.confirm(__("Schedule this message for the selected audience? Actual sending requires explicit site configuration."), () => {
					frappe.call({method: "frappe_education_kenya.messaging.schedule", args: {name: frm.doc.name}, freeze: true})
						.then(() => frm.reload_doc());
				});
			});
		}
	},
});
