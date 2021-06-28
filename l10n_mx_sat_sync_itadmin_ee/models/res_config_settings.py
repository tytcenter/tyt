# -*- coding: utf-8 -*-

from odoo import models, api, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _selection_product_type(self):
        product_obj = self.env['product.product']
        return product_obj._fields.get('type')._description_selection(product_obj.env)

    l10n_mx_esignature_ids = fields.Many2many(related='company_id.l10n_mx_esignature_ids', 
        string='MX E-signature', readonly=False)
    last_cfdi_fetch_date = fields.Datetime("Last CFDI fetch date", related="company_id.last_cfdi_fetch_date", readonly=False)
    product_type_default = fields.Selection(selection=_selection_product_type, string='Crear Productos', required=True,
        help='A stockable product is a product for which you manage stock. The "Inventory" app has to be installed.\n'
             'A consumable product, on the other hand, is a product for which stock is not managed.\n'
             'A service is a non-material product you provide.\n'
             'A digital content is a non-material product you sell online. The files attached to the products are the one that are sold on '
             'the e-commerce such as e-books, music, pictures,... The "Digital Product" module has to be installed.')
    
    solo_documentos_de_proveedor = fields.Boolean("Solo documentos de proveedor", related="company_id.solo_documentos_de_proveedor", readonly=False)
    
        
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            product_type_default=self.env['ir.config_parameter'].with_user(self.env.user).get_param('l10n_mx_sat_sync_itadmin.product_type_default')
        )
        return res

    
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].with_user(self.env.user).set_param('l10n_mx_sat_sync_itadmin.product_type_default', self.product_type_default)
        return res
    
    
    def import_sat_invoice(self):
        self.company_id.download_cfdi_invoices()
        return True