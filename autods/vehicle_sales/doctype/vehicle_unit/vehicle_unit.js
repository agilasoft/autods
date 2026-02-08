// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle Unit", {
	refresh(frm) {
		if (frm.doc.code && frm.doc.item && frm.doc.warehouse && !frm.is_new()) {
			frm.add_custom_button(__("Add cost to inventory"), () => {
				const d = new frappe.ui.Dialog({
					title: __("Add cost to vehicle serial"),
					fields: [
						{
							fieldname: "amount_to_add",
							fieldtype: "Currency",
							label: __("Amount to add"),
							reqd: 1,
						},
						{
							fieldname: "reason",
							fieldtype: "Small Text",
							label: __("Reason (optional)"),
						},
					],
					primary_action_label: __("Add cost"),
					primary_action(values) {
						frappe.call({
							method: "autods.vehicle_sales.add_cost_to_vehicle_serial.add_cost_to_vehicle_serial",
							args: {
								vehicle_unit: frm.doc.name,
								amount_to_add: values.amount_to_add,
								reason: values.reason || undefined,
							},
							callback(r) {
								if (r.message && r.message.message) {
									frappe.show_alert({ message: r.message.message, indicator: "green" });
								}
								if (r.message && r.message.stock_reconciliation) {
									frappe.set_route("Form", "Stock Reconciliation", r.message.stock_reconciliation);
								}
								frm.reload_doc();
							},
						});
						d.hide();
					},
				});
				d.show();
			}, __("Actions"));
		}
	},
});
