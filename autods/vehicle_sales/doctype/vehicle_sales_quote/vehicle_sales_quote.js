// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vehicle Sales Quote", {
	refresh: function (frm) {
		if (frm.doc.docstatus !== 1) {
			return;
		}

		if (["Cancelled", "Lost", "Expired", "Ordered"].indexOf(frm.doc.status) >= 0) {
			return;
		}

		frm.add_custom_button(
			__("Sales Order"),
			function () {
				frappe.model.open_mapped_doc({
					method: "autods.vehicle_sales.doctype.vehicle_sales_quote.vehicle_sales_quote.make_sales_order",
					frm: frm,
				});
			},
			__("Create")
		);

		frm.add_custom_button(
			__("Mark Lost"),
			function () {
				frappe.prompt(
					[
						{
							fieldname: "lost_reason",
							fieldtype: "Small Text",
							label: __("Lost Reason"),
							reqd: 1,
						},
						{
							fieldname: "competitor",
							fieldtype: "Data",
							label: __("Competitor"),
						},
					],
					function (values) {
						frm.call({
							method: "declare_lost",
							doc: frm.doc,
							args: values,
							callback: function () {
								frm.reload_doc();
							},
						});
					},
					__("Mark Quote Lost"),
					__("Mark Lost")
				);
			},
			__("Create")
		);
	},

	base_price: function (frm) {
		calculate_quote_totals(frm);
	},

	discount_amount: function (frm) {
		calculate_quote_totals(frm);
	},

	additional_discount_percentage: function (frm) {
		calculate_quote_totals(frm);
	},

	accessories_add: function (frm) {
		calculate_quote_totals(frm);
	},

	accessories_remove: function (frm) {
		calculate_quote_totals(frm);
	},
});

frappe.ui.form.on("Vehicle Sales Quote Accessory", {
	qty: function (frm, cdt, cdn) {
		calculate_accessory_amount(frm, cdt, cdn);
	},

	rate: function (frm, cdt, cdn) {
		calculate_accessory_amount(frm, cdt, cdn);
	},

	installation_cost: function (frm, cdt, cdn) {
		calculate_accessory_amount(frm, cdt, cdn);
	},
});

function calculate_accessory_amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	// Match server: blank/0 qty defaults to 1
	const qty = flt(row.qty, 2) || 1;
	row.qty = qty;

	const amount = flt(qty * flt(row.rate, 2) + flt(row.installation_cost, 2), 2);
	row.amount = amount;
	frm.refresh_field("accessories");
	calculate_quote_totals(frm);
}

function calculate_quote_totals(frm) {
	let accessories_total = 0;
	(frm.doc.accessories || []).forEach((row) => {
		accessories_total += flt(row.amount, 2);
	});
	accessories_total = flt(accessories_total, 2);

	const net_total = flt(flt(frm.doc.base_price, 2) + accessories_total, 2);

	let discount = flt(frm.doc.discount_amount, 2);
	if (!discount && flt(frm.doc.additional_discount_percentage)) {
		discount = flt((net_total * flt(frm.doc.additional_discount_percentage)) / 100, 2);
		frm.doc.discount_amount = discount;
		frm.refresh_field("discount_amount");
	}

	const taxable = Math.max(net_total - discount, 0);
	const total_taxes = calculate_taxes(frm, taxable);
	const grand_total = flt(taxable + total_taxes, 2);

	frm.set_value("accessories_total", accessories_total);
	frm.set_value("net_total", net_total);
	frm.set_value("total_taxes_and_charges", total_taxes);
	frm.set_value("grand_total", grand_total);
}

function calculate_taxes(frm, taxable) {
	let total = 0;
	(frm.doc.taxes || []).forEach((row) => {
		const rate = flt(row.rate, 6);
		let tax_amount = flt(row.tax_amount, 2);

		if (row.charge_type === "On Net Total") {
			tax_amount = flt((taxable * rate) / 100, 2);
		} else if (row.charge_type === "Actual") {
			tax_amount = flt(row.tax_amount, 2);
		}

		row.tax_amount = tax_amount;
		row.base_tax_amount = flt(tax_amount * flt(frm.doc.conversion_rate || 1), 2);
		total += tax_amount;
		row.total = flt(taxable + total, 2);
		row.base_total = flt(row.total * flt(frm.doc.conversion_rate || 1), 2);
	});

	if ((frm.doc.taxes || []).length) {
		frm.refresh_field("taxes");
	}
	return flt(total, 2);
}
