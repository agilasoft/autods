// Shop-local datetime helpers: display/save without user-timezone conversion.

frappe.provide("autods.service_datetime");

$.extend(autods.service_datetime, {
	get_system_timezone() {
		return (
			(frappe.boot.time_zone && frappe.boot.time_zone.system) ||
			frappe.sys_defaults.time_zone
		);
	},

	format_system_datetime(val) {
		if (!val) {
			return "";
		}
		const system_tz = autods.service_datetime.get_system_timezone();
		const user_date_fmt = frappe.datetime.get_user_date_fmt().toUpperCase();
		const user_time_fmt = frappe.datetime.get_user_time_fmt();
		const display_fmt = `${user_date_fmt} ${user_time_fmt}`;
		let m = moment.tz(val, frappe.defaultDatetimeFormat, system_tz);
		if (!m.isValid()) {
			m = moment.tz(val, system_tz);
		}
		return m.isValid() ? m.format(display_fmt) : String(val);
	},

	parse_system_datetime(val) {
		if (!val) {
			return "";
		}
		const system_tz = autods.service_datetime.get_system_timezone();
		let m = moment.tz(val, frappe.defaultDatetimeFormat, system_tz);
		if (!m.isValid()) {
			const user_date_fmt = frappe.datetime.get_user_date_fmt().toUpperCase();
			const user_time_fmt = frappe.datetime.get_user_time_fmt();
			const user_fmt = `${user_date_fmt} ${user_time_fmt}`;
			m = moment.tz(val, [user_fmt.replace("YYYY", "YY"), user_fmt], system_tz);
		}
		return m.isValid() ? m.format(frappe.defaultDatetimeFormat) : "Invalid date";
	},

	format_system_datetime_long(val) {
		if (!val) {
			return "—";
		}
		const system_tz = autods.service_datetime.get_system_timezone();
		let m = moment.tz(val, frappe.defaultDatetimeFormat, system_tz);
		if (!m.isValid()) {
			m = moment.tz(val, system_tz);
		}
		return m.isValid() ? m.format("dddd, MMMM D, YYYY – LT") : String(val);
	},

	patch_system_datetime_control(frm, fieldname) {
		const field = frm.fields_dict[fieldname];
		if (!field || field._autods_system_tz_patched) {
			return;
		}
		field._autods_system_tz_patched = true;

		field.format_for_input = function (value) {
			if (!value) {
				return "";
			}
			return autods.service_datetime.format_system_datetime(value);
		};

		field.parse = function (value) {
			if (value) {
				value = this.eval_expression(value, "datetime");
				value = autods.service_datetime.parse_system_datetime(value);
				if (value === "Invalid date") {
					value = "";
				}
			}
			return value;
		};

		field.get_start_date = function () {
			this.value = this.value == null || this.value === "" ? undefined : this.value;
			if (!this.value) {
				return undefined;
			}
			const system_tz = autods.service_datetime.get_system_timezone();
			const m = moment.tz(this.value, frappe.defaultDatetimeFormat, system_tz);
			return m.isValid() ? m.toDate() : frappe.datetime.str_to_obj(this.value);
		};

		field.set_description = function () {
			const time_zone = autods.service_datetime.get_system_timezone();
			if (!this.df.hide_timezone) {
				if (!this.df.description) {
					this.df.description = time_zone;
				} else if (!this.df.description.includes(time_zone)) {
					this.df.description += "<br>" + time_zone;
				}
			}
			frappe.ui.form.ControlData.prototype.set_description.call(this);
		};

		field.set_disp_area = function (value) {
			value = this.value || value;
			if (this.disp_area) {
				const display = value
					? autods.service_datetime.format_system_datetime(value)
					: "";
				$(this.disp_area).html(display);
			}
		};

		field.set_description();
		if (field.value) {
			field.set_formatted_input(field.value);
		}
		if (field.disp_status === "Read" && field.value) {
			field.set_disp_area(field.value);
		}
	},
});
