/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ListController } from "@web/views/list/list_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanDropdownMenuWrapper } from "@web/views/kanban/kanban_dropdown_menu_wrapper";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { FileUploader } from "@web/views/fields/file_handler";
import rpc from 'web.rpc';

const { Component, useState } = owl;
import core from 'web.core';

export class ListItadmin extends ListController {

    async _onClickImportarXML (event) {
        debugger;
        event.stopPropagation();
        var self = this;
        return this.model.action.doAction({
            name: "Attach Files",
            type: 'ir.actions.act_window',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_model: 'multi.file.attach.xmls.wizard'
        });

    }

    async _onClickDescargaXDia (event) {
        event.stopPropagation();
        var self = this;

        return this.model.action.doAction({
            name: "Descarga x Dia",
            type: 'ir.actions.act_window',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_model: 'descarga.x.dia.wizard'
        });
    }

    async _onImportFIELSatInvoice (event) {
    debugger;
        event.stopPropagation();
        var self = this;
        rpc.query({
            model: 'res.company',
            method: 'import_current_company_invoice',
//            args: [],

        }).then(function () {
            return;
        });
    }

    async _onClickSincronizarDocumentos (event) {
       event.stopPropagation();
       var self = this;
       rpc.query({
             model: 'ir.attachment',
             method: 'update_status_from_ir_attachment_document',
//             args: [],
        }).then(function () {
            return;
        });
    }
}


export const itadmin = {
    ...listView,
    Controller: ListItadmin,
    buttonTemplate: "l10n_mx_sat_sync_itadmin_ee.ListView.Buttons",
};
registry.category("views").add("itadmin_tree", itadmin);
