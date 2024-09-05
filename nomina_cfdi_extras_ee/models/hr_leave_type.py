# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
#import logging
#_logger = logging.getLogger(__name__)

class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    code = fields.Char('Código')

class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    ######### Vacaciones
    dias_de_vacaciones_disponibles = fields.Integer("Dias de vacaciones disponibles")

    ######### Incapacidades
    ramo_de_seguro = fields.Selection([('Riesgo de trabajo', 'Riesgo de trabajo'), ('Enfermedad general', 'Enfermedad general'), ('Maternidad','Maternidad')], string='Ramo de seguro')
    tipo_de_riesgo = fields.Selection([('Accidente de trabajo', 'Accidente de trabajo'), ('Accidente de trayecto', 'Accidente de trayecto'), ('Enfermedad de trabajo','Enfermedad de trabajo')], string='Tipo de riesgo')
    secuela = fields.Selection([('Ninguna', 'Ninguna'), ('Incapacidad temporal', 'Incapacidad temporal'), ('Valuación inicial provisional','Valuación inicial provisional'), ('Valuación inicial definitiva', 'Valuación inicial definitiva')], string='Secuela')
    control = fields.Selection([('Unica', 'Unica'), ('Inicial', 'Inicial'), ('Subsecuente','Subsecuente'), ('Alta médica o ST-2', 'Alta médica o ST-2')], string='Control')
    control2 = fields.Selection([('01', 'Prenatal o ST-3'), ('02', 'Enalce'), ('03','Postnatal')], string='Control maternidad')
    porcentaje = fields.Char('Porcentaje')
    descripcion = fields.Text('Descripción de la enfermedad')
    folio_incapacidad = fields.Char('Folio de incapacidad')

    type_vac = fields.Boolean('Vac', compute='_compute_type')
    type_inc = fields.Boolean('Inc', compute='_compute_type')

    ######### Vacaciones
    @api.onchange('employee_id', 'holiday_status_id')
    def _onchange_employee_id(self):
        for leave in self:
           if leave.employee_id and leave.holiday_status_id.code == 'VAC':
               contract = leave.employee_id.contract_id
               if contract:
                   leave.dias_de_vacaciones_disponibles = sum(vacacione.dias for vacacione in contract.tabla_vacaciones)

    @api.onchange('number_of_days_display')
    def _onchange_dias(self):
        for leave in self:
           if leave.holiday_status_id.code == 'VAC':
              if leave.number_of_days_display and leave.number_of_days_display > leave.dias_de_vacaciones_disponibles:
                  raise UserError(_("%s no tiene suficientes dias de vacaciones") % leave.employee_id.name)

    @api.onchange('holiday_status_id')
    def _compute_type(self):
        for leave in self:
           leave.type_vac = False
           leave.type_inc = False
           if leave.holiday_status_id.code == 'VAC':
               leave.type_vac = True
           if leave.holiday_status_id.code == 'INC_MAT' or  leave.holiday_status_id.code == 'INC_RT' or leave.holiday_status_id.code == 'INC_EG':
               leave.type_inc = True

    def action_approve(self):
        for leave in self:
           if leave.holiday_status_id.code == 'VAC':
              vac_adelantada = self.env['ir.config_parameter'].sudo().get_param('nomina_cfdi_extras_ee.vacaciones_adelantadas')

              if leave.number_of_days_display and leave.number_of_days_display > leave.dias_de_vacaciones_disponibles:
                 if not vac_adelantada:
                    raise UserError(_("%s no tiene suficientes dias de vacaciones") % leave.employee_id.name)
                 else:
                    contract = leave.employee_id.contract_id
                    contract.vacaciones_adelantadas += leave.number_of_days_display
              else:
                 dias = leave.number_of_days_display
                 if leave.employee_id and dias:
                     contract = leave.employee_id.contract_id
                     if contract:
                        for vac in contract.tabla_vacaciones.sorted(key=lambda object1: object1.ano):
                            if dias <= vac.dias:
                               vac.write({'dias':vac.dias - dias})
                               break
                            elif dias > vac.dias:
                               dias = dias - vac.dias
                               vac.write({'dias':0})

        return super(HolidaysRequest, self).action_approve()

    def action_refuse(self):
        for leave in self:
           if leave.state == 'validate':
              if leave.holiday_status_id.code == 'VAC':
                 #vac_adelantada = self.env['ir.config_parameter'].sudo().get_param('nomina_cfdi_extras_ee.vacaciones_adelantadas')
                 if leave.number_of_days_display and leave.number_of_days_display > leave.dias_de_vacaciones_disponibles:
                    contract = leave.employee_id.contract_id
                    contract.vacaciones_adelantadas -= leave.number_of_days_display
                 else:
                    contract = leave.employee_id.contract_id
                    if contract:
                       vac = contract.tabla_vacaciones.sorted(key=lambda object1: object1.ano)
                       if vac:
                          saldo_ant = vac[0].dias + leave.number_of_days_display
                          vac[0].write({'dias':saldo_ant})

        return super(HolidaysRequest, self).action_refuse()
