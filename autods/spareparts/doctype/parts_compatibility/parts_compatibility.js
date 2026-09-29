// Copyright (c) 2025, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Parts Compatibility", {
	applies_to_all_vehicles(frm) {
		if (frm.doc.applies_to_all_vehicles) {
			frm.set_value("vehicle_make", "");
			frm.set_value("vehicle_model", "");
			frm.set_value("vehicle_variant", "");
			frm.set_value("transmission_type", "");
			frm.set_value("year_from", "");
			frm.set_value("year_to", "");
		}
	},
});
