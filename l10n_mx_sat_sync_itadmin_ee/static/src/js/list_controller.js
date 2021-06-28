odoo.define('l10n_mx_sat_sync_itadmin_ee.ListController', function (require) {
"use strict";

var ListController = require('web.ListController');

ListController.include({
	renderButtons: function ($node) {
		this._super($node)
		if (this.modelName==='ir.attachment' && !this.noLeaf){
			var context = this.model.get(this.handle, {raw: true}).getContext();
			if (context.is_fiel_attachment!==undefined && context.is_fiel_attachment==true){
				if (this.$buttons.find(".o_list_button_discard").length){
					var $import_button = $("<button type='button' class='btn btn-default btn-sm o_list_button_importar_xml_fiel_invoice_from_sat' accesskey='xml'>Importar XML</button>");
					this.$buttons.find(".o_list_button_discard").after($import_button);
					this.$buttons.on('click', '.o_list_button_importar_xml_fiel_invoice_from_sat', this._onClickImportarXML.bind(this));
					
					var $import_button = $("<button type='button' class='btn btn-default btn-sm o_list_button_descarga_x_dia_fiel_invoice_from_sat' accesskey='dia'>Descarga Dia</button>");
					this.$buttons.find(".o_list_button_discard").after($import_button);
					this.$buttons.on('click', '.o_list_button_descarga_x_dia_fiel_invoice_from_sat', this._onClickDescargaXDia.bind(this));
					
					/*var $import_button = $("<button type='button' class='btn btn-default btn-sm o_list_button_reconcile_fiel_invoice_from_sat' accesskey='if'>Conciliar</button>");
					this.$buttons.find(".o_list_button_discard").after($import_button);
					this.$buttons.on('click', '.o_list_button_reconcile_fiel_invoice_from_sat', this._onReconcileFIELSatInvoice.bind(this));*/
					var $import_button = $("<button type='button' class='btn btn-default btn-sm o_list_button_import_fiel_invoice_from_sat' accesskey='if'>Sincronizar SAT</button>");
					this.$buttons.find(".o_list_button_discard").after($import_button);
					this.$buttons.on('click', '.o_list_button_import_fiel_invoice_from_sat', this._onImportFIELSatInvoice.bind(this));
				}
			}
		}
	},
	_onImportFIELSatInvoice: function (event) {
        event.stopPropagation();
        var self = this;
        self._rpc({
            model: 'res.company',
            method: 'import_current_company_invoice',
            args: [],
            
        }).then(function () {
            return;
        });
    },
    /*_onReconcileFIELSatInvoice: function (event) {
        event.stopPropagation();
        var self = this;
        var select_ids = _.map(this.selectedRecords, function (record) {return self.model.get(record).res_id });
        if (select_ids.length==0){
        	alert("Please select atleast one Attachment.");
        	return;
        }
        return this.do_action({
            name: "Reconciliar",
            type: 'ir.actions.act_window',
            view_mode: 'form',
            views: [[false, 'form']],
            context:{'select_ids':select_ids},
            target: 'new',
            res_model: 'reconcile.vendor.cfdi.xml.bill'
        });
        
    },*/
    _onClickImportarXML : function (event) {
        event.stopPropagation();
        var self = this;
        return this.do_action({
            name: "Attach Files",
            type: 'ir.actions.act_window',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_model: 'multi.file.attach.xmls.wizard'
        });
        
    },
    _onClickDescargaXDia: function (event) {
        event.stopPropagation();
        var self = this;
        
        return this.do_action({
            name: "Descarga x Dia",
            type: 'ir.actions.act_window',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_model: 'descarga.x.dia.wizard'
        });
        
    },
});

});