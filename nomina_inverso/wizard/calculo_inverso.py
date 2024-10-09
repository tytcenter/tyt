# -*- coding: utf-8 -*-
from odoo import models, fields,api,_

class calculoInverso(models.TransientModel):
    _name="calculo.inverso"
    
    monto = fields.Float(string="Monto del periodo")
    ultima_nomina = fields.Boolean(string="Ultima nomina del mes", default=False)
    mes = fields.Selection(
        selection=[('01', 'Enero / Periodo 1'), 
                   ('02', 'Febrero / Periodo 2'), 
                   ('03', 'Marzo / Periodo 3'),
                   ('04', 'Abril / Periodo 4'), 
                   ('05', 'Mayo / Periodo 5'),
                   ('06', 'Junio / Periodo 6'),
                   ('07', 'Julio / Periodo 7'),
                   ('08', 'Agosto / Periodo 8'),
                   ('09', 'Septiembre / Periodo 9'),
                   ('10', 'Octubre / Periodo 10'),
                   ('11', 'Noviembre / Periodo 11'),
                   ('12', 'Diciembre / Periodo 12'),
                   ],
        string=_('Mes de la nómina'))

    def call_compute_sueldo_neto(self):
        #self.hr_contract_id.compute_sueldo_neto()
        ctx = self._context.copy()
        active_ids = ctx.get('active_ids')
        if active_ids:
            hr_contract = self.env['hr.contract'].browse(active_ids)
            hr_contract.update_values(self.ultima_nomina, self.mes)
            hr_contract.compute_sueldo_neto(self.monto)
