odoo.define('l10n_mx_sat_sync_itadmin_ee.DataManager', function (require) {
"use strict";

	var DataManager = require('web.DataManager');
	var session = require('web.session');
	
	DataManager.include({
		load_action: function (action_id, additional_context) {
			if (additional_context==undefined){
				additional_context={};
			}
			additional_context.allowed_company_ids = session.user_context.allowed_company_ids;
			debugger;
			return this._super(action_id, additional_context);
		}	
	});
});