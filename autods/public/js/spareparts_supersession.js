// Suggest an in-stock supersession when a spare part line has no bin qty.

frappe.ui.form.on("Repair Order Charges", {
	item(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row || row.service_item_type !== "Spareparts" || !row.item) {
			return;
		}
		frappe.call({
			method: "autods.spareparts.supersession.get_supersession_suggestion",
			args: {
				item_code: row.item,
				warehouse: row.warehouse || "",
			},
			callback(r) {
				const suggestion = r && r.message;
				if (!suggestion || !suggestion.item_code) {
					return;
				}
				frappe.msgprint({
					title: __("Superseded part in stock"),
					message: __(
						"{0} has no stock. {1} ({2}) is an active replacement with qty {3}.",
						[
							row.item,
							suggestion.item_code,
							suggestion.item_name || "",
							suggestion.actual_qty,
						]
					),
					indicator: "orange",
				});
			},
		});
	},
});
