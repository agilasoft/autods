# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class EmployeeServiceSkill(Document):
	def validate(self):
		self.skill_name = (self.skill_name or "").strip()
		self._validate_duplicate()

	def _validate_duplicate(self):
		if not self.employee or not self.skill_name:
			return
		existing = frappe.db.sql(
			"""
			SELECT name FROM `tabEmployee Service Skill`
			WHERE employee = %s AND LOWER(skill_name) = LOWER(%s) AND name != %s
			LIMIT 1
			""",
			(self.employee, self.skill_name, self.name or ""),
		)
		if existing:
			frappe.throw(_("This skill is already recorded for {0}.").format(self.employee))
