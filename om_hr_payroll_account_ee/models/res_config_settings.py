# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tipo_de_poliza = fields.Selection([('Por empleado', 'Por empleado'), ('Por nómina', 'Por procesamiento')], string='Tipo de poliza')
    compacta = fields.Boolean(string='Compacta (no separa por cuentas analíticas)')
    tipo_de_compacta = fields.Selection([('01', 'Por cuentas contables'), ('02', 'Por departamento')], string='Agrupar por')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        param_obj = self.env['ir.config_parameter'].sudo()
        res.update(
            tipo_de_poliza = param_obj.get_param('om_hr_payroll_account_ee.tipo_de_poliza'),
            compacta = param_obj.get_param('om_hr_payroll_account_ee.compacta'),
            tipo_de_compacta = param_obj.get_param('om_hr_payroll_account_ee.tipo_de_compacta'),
        )
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        param_obj = self.env['ir.config_parameter'].sudo()
        param_obj.set_param('om_hr_payroll_account_ee.tipo_de_poliza', self.tipo_de_poliza)
        param_obj.set_param('om_hr_payroll_account_ee.compacta', self.compacta)
        param_obj.set_param('om_hr_payroll_account_ee.tipo_de_compacta', self.tipo_de_compacta)
        return res
