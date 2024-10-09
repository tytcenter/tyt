/** @odoo-module **/
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

export class CustomListController extends ListController {

    async _onClickEntregaFondoCaja (event) {
        event.stopPropagation();
        var self = this;
        return this.model.action.doAction({
            name: "Altas y Bajas",
            type: 'ir.actions.act_window',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            res_model: 'entrega.fondo.caja'
        });
    }
}

registry.category('views').add('caja_nomina_list', {
    ...listView,
    Controller: CustomListController,
    buttonTemplate: "nomina_cfdi.ListView.Buttons",
});
