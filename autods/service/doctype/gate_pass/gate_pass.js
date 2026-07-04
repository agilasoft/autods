// Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
// For license information, please see license.txt

const EXIT_GATE_PASS_STATUSES = ['Exit Only', 'Completed'];

function autods_is_exit_gate_pass(frm) {
	const gate_pass_type = (frm.doc.gate_pass_type || '').trim();
	const status = (frm.doc.status || '').trim();
	if (gate_pass_type === 'Exit') {
		return true;
	}
	return EXIT_GATE_PASS_STATUSES.includes(status);
}

function autods_validate_gate_pass_job_cards(frm) {
	if (!autods_is_exit_gate_pass(frm)) {
		return;
	}
	if (!frm.doc.job_card && !frm.doc.repair_order) {
		frappe.throw(__('Link a Repair Order or Job Card before saving an exit/completed Gate Pass.'));
	}
	if (!frm.doc.job_card) {
		return;
	}
	return frappe.db.get_value('Job Card', frm.doc.job_card, 'status').then((r) => {
		const status = (r && r.message && r.message.status) || '';
		if (status !== 'Completed') {
			frappe.throw(
				__('Job Card {0} must be Completed before creating an exit/completed Gate Pass.', [
					frm.doc.job_card,
				]),
			);
		}
	});
}

frappe.ui.form.on('Gate Pass', {
	validate(frm) {
		return autods_validate_gate_pass_job_cards(frm);
	},
	status(frm) {
		if (autods_is_exit_gate_pass(frm) && frm.doc.job_card) {
			autods_validate_gate_pass_job_cards(frm);
		}
	},
	gate_pass_type(frm) {
		if (autods_is_exit_gate_pass(frm) && frm.doc.job_card) {
			autods_validate_gate_pass_job_cards(frm);
		}
	},
	job_card(frm) {
		if (autods_is_exit_gate_pass(frm) && frm.doc.job_card) {
			autods_validate_gate_pass_job_cards(frm);
		}
	},
});
