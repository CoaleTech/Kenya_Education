/**
 * Frappe Education Kenya — Desk Bundle
 *
 * Client-side logic for Kenya-specific features:
 * - Student form: CBC history, transitions, transport/meal subscriptions
 * - Transport Route: subscriber + revenue rollup
 * - Daily Meal Record: total cost calculation
 */

frappe.provide("frappe_education_kenya");

// Student Form Enhancements
frappe.ui.form.on("Student", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(
			__("View CBC History"),
			() => {
				frappe.route_options = { student: frm.doc.name };
				frappe.set_route("List", "Assessment Result");
			},
			__("Kenya")
		);

		frm.add_custom_button(
			__("Student Transition"),
			() => {
				frappe.route_options = { student: frm.doc.name };
				frappe.set_route("List", "Student Transition");
			},
			__("Kenya")
		);

		// Transport / meals buttons are gated by Education Kenya Settings.
		frappe.db.get_doc("Education Kenya Settings").then((settings) => {
			if (settings.enable_transport) {
				frm.add_custom_button(
					__("Transport Subscription"),
					() => {
						frappe.route_options = { student: frm.doc.name };
						frappe.set_route("List", "Transport Subscription");
					},
					__("Kenya")
				);
			}
			if (settings.enable_meals) {
				frm.add_custom_button(
					__("Meal Subscription"),
					() => {
						frappe.route_options = { student: frm.doc.name };
						frappe.set_route("List", "Student Meal Subscription");
					},
					__("Kenya")
				);
			}
		});
	},

	// Auto-assign CBC level based on program
	program(frm) {
		if (!frm.doc.program || frm.doc.kenya_cbc_level) return;
		frappe.db.get_value("Program", frm.doc.program, "cbc_level_mapping").then((r) => {
			if (r.message && r.message.cbc_level_mapping) {
				frm.set_value("kenya_cbc_level", r.message.cbc_level_mapping);
			}
		});
	},
});

// Transport Route — subscriber and revenue rollup
frappe.ui.form.on("Transport Route", {
	refresh(frm) {
		frm.trigger("calculate_revenue");
	},

	term_fee(frm) {
		frm.trigger("calculate_revenue");
	},

	calculate_revenue(frm) {
		if (frm.is_new()) return;
		frappe.call({
			method: "frappe.client.get_count",
			args: {
				doctype: "Transport Subscription",
				filters: { route: frm.doc.name, subscription_status: "Active" },
			},
			callback(r) {
				if (r.message === undefined) return;
				const revenue = (r.message * (frm.doc.term_fee || 0)) / 3; // ~monthly (3-month term)
				// Only write when stale, so opening the form never dirties it.
				if (frm.doc.total_subscribers !== r.message) {
					frm.set_value("total_subscribers", r.message);
				}
				if (frm.doc.monthly_revenue !== revenue) {
					frm.set_value("monthly_revenue", revenue);
				}
			},
		});
	},
});

// Daily Meal Record — total cost calculation
frappe.ui.form.on("Daily Meal Record", {
	students_served(frm) {
		frm.trigger("calculate_total_cost");
	},

	cost_per_serving(frm) {
		frm.trigger("calculate_total_cost");
	},

	calculate_total_cost(frm) {
		const total = (frm.doc.students_served || 0) * (frm.doc.cost_per_serving || 0);
		if (frm.doc.total_cost !== total) {
			frm.set_value("total_cost", total);
		}
	},
});
