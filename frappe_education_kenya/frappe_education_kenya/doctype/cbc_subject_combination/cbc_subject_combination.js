frappe.ui.form.on("CBC Subject Combination", {
	refresh(frm) {
		set_track_options(frm);
	},
	pathway(frm) {
		frm.set_value("track", "");
		set_track_options(frm);
	},
});

function set_track_options(frm) {
	if (!frm.doc.pathway) {
		frm.set_df_property("track", "options", []);
		return;
	}
	frappe.db.get_doc("CBC Pathway", frm.doc.pathway).then((pathway) => {
		if (pathway.name !== frm.doc.pathway) return;
		frm.set_df_property("track", "options", (pathway.tracks || []).map((row) => ({
			value: row.track_name,
			label: row.is_confirmed ? row.track_name : __("{0} (draft label)", [row.track_name]),
		})));
	});
}
