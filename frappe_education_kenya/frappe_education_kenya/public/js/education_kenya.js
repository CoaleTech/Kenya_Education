/**
 * Frappe Education Kenya — Main JavaScript Bundle
 *
 * Client-side logic for Kenya-specific features:
 * - CBC Assessment Performance Level auto-calculation
 * - Student form enhancements
 * - Transport and Meals UI interactions
 */

frappe.provide("frappe_education_kenya");

frappe_education_kenya.CBCAssessment = class {
    constructor(frm) {
        this.frm = frm;
        this.setup();
    }

    setup() {
        // Auto-populate performance level label based on selection
        this.frm.fields_dict.performance_level.$input.on("change", () => {
            this.update_performance_level_label();
        });
    }

    update_performance_level_label() {
        const pl = this.frm.doc.performance_level;
        const labels = {
            "PL1": "Exceeds Expectations",
            "PL2": "Meets Expectations",
            "PL3": "Approaches Expectations",
            "PL4": "Below Expectations"
        };
        this.frm.set_value("performance_level_label", labels[pl] || "");
    }
};

// Student Form Enhancements
frappe.ui.form.on("Student", {
    refresh: function(frm) {
        // Add Kenya-specific buttons
        if (!frm.is_new()) {
            frm.add_custom_button(__("View CBC History"), function() {
                frappe.route_options = { student: frm.doc.name };
                frappe.set_route("List", "CBC Assessment Result", { student: frm.doc.name });
            }, __("Kenya"));

            frm.add_custom_button(__("Student Transition"), function() {
                frappe.route_options = { student: frm.doc.name };
                frappe.set_route("List", "Student Transition", { student: frm.doc.name });
            }, __("Kenya"));

            if (frappe.boot.sysdefaults.enable_transport) {
                frm.add_custom_button(__("Transport Subscription"), function() {
                    frappe.route_options = { student: frm.doc.name };
                    frappe.set_route("List", "Transport Subscription", { student: frm.doc.name });
                }, __("Kenya"));
            }

            if (frappe.boot.sysdefaults.enable_meals) {
                frm.add_custom_button(__("Meal Subscription"), function() {
                    frappe.route_options = { student: frm.doc.name };
                    frappe.set_route("List", "Student Meal Subscription", { student: frm.doc.name });
                }, __("Kenya"));
            }
        }
    },

    // Auto-assign CBC level based on program
    program: function(frm) {
        if (frm.doc.program && !frm.doc.kenya_cbc_level) {
            frappe.db.get_value("Program", frm.doc.program, "cbc_level_mapping")
                .then(r => {
                    if (r.message && r.message.cbc_level_mapping) {
                        frm.set_value("kenya_cbc_level", r.message.cbc_level_mapping);
                    }
                });
        }
    }
});

// CBC Assessment Result Form
frappe.ui.form.on("CBC Assessment Result", {
    refresh: function(frm) {
        // Calculate score percentage
        if (frm.doc.raw_score && frm.doc.maximum_score) {
            const pct = (frm.doc.raw_score / frm.doc.maximum_score) * 100;
            frm.set_value("score_percentage", pct.toFixed(2));

            // Auto-assign performance level based on percentage
            let pl = "";
            if (pct >= 80) pl = "PL1";
            else if (pct >= 65) pl = "PL2";
            else if (pct >= 50) pl = "PL3";
            else pl = "PL4";

            frm.set_value("performance_level", pl);
        }
    },

    raw_score: function(frm) {
        frm.trigger("refresh");
    },

    maximum_score: function(frm) {
        frm.trigger("refresh");
    }
});

// Transport Route — Calculate totals
frappe.ui.form.on("Transport Route", {
    refresh: function(frm) {
        frm.trigger("calculate_revenue");
    },

    calculate_revenue: function(frm) {
        if (frm.doc.route_code) {
            frappe.call({
                method: "frappe.client.get_count",
                args: {
                    doctype: "Transport Subscription",
                    filters: {
                        route: frm.doc.name,
                        subscription_status: "Active"
                    }
                },
                callback: function(r) {
                    if (r.message !== undefined) {
                        frm.set_value("total_subscribers", r.message);
                        const revenue = r.message * (frm.doc.term_fee || 0);
                        frm.set_value("monthly_revenue", revenue / 3); // Approximate monthly
                    }
                }
            });
        }
    }
});

// Daily Meal Record — Calculate total cost
frappe.ui.form.on("Daily Meal Record", {
    refresh: function(frm) {
        frm.trigger("calculate_total_cost");
    },

    students_served: function(frm) {
        frm.trigger("calculate_total_cost");
    },

    cost_per_serving: function(frm) {
        frm.trigger("calculate_total_cost");
    },

    calculate_total_cost: function(frm) {
        const total = (frm.doc.students_served || 0) * (frm.doc.cost_per_serving || 0);
        frm.set_value("total_cost", total);
    }
});
