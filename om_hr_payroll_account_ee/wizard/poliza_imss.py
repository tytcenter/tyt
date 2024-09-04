# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from collections import defaultdict
import io
from odoo.tools.misc import xlwt
import base64
import logging

_logger = logging.getLogger(__name__)

class WizardPolizaIMSS(models.TransientModel):
    _name = 'wizard.poliza.imss'
    _description = 'Poliza IMSS'

    date = fields.Date(string='Fecha')
    hr_payslip_run_ids = fields.Many2many('hr.payslip.run',string="Procesamientos de nómina")
    journal_id = fields.Many2one("account.journal",'Diario')
    tablas_id = fields.Many2one('tablas.cfdi','Tabla CFDI')

    def create_poliza_imss(self):
       line_ids = []
       debit_sum = 0.0
       credit_sum = 0.0
       date = self.date
       currency =  self.env["res.currency"].search([('name', '=', 'MXN')], limit=1)

       name = _('Poliza IMSS %s') % (date)
       move_dict = {
                    'narration': name,
                    'ref': '',
                    'journal_id': self.journal_id.id,
                    'date': date,
       }

       for hr_payslip_run_id in self.hr_payslip_run_ids:
           _logger.info('payslip run')
           for slip in hr_payslip_run_id.slip_ids:
                _logger.info('payslip %s', slip.name)
                if slip.state in ("cancel", "draft"):
                     _logger.info('candel draft')
                     continue

                if slip.contract_id.tablas_cfdi_id.id != self.tablas_id.id:
                     _logger.info('sale tables')
                     continue

                _logger.info('sigue adelante')
                #cuota fija patronal
                if self.tablas_id.pat_cuota_fija_pat_deb:
                        debit_line = (0, 0, {
                            'name': 'Cuota fija patronal',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_cuota_fija_pat_deb.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_cuota_fija_pat > 0.0 and slip.pat_cuota_fija_pat or 0.0,
                            'credit': slip.pat_cuota_fija_pat < 0.0 and -slip.pat_cuota_fija_pat or 0.0,
                            #'analytic_distribution': debit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
                        _logger.info('cuota fija patronal deb')

                if self.tablas_id.pat_cuota_fija_pat_cre:
                        credit_line = (0, 0, {
                            'name': 'Cuota fija patronal',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_cuota_fija_pat_cre.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_cuota_fija_pat < 0.0 and -slip.pat_cuota_fija_pat or 0.0,
                            'credit': slip.pat_cuota_fija_patunt > 0.0 and slip.pat_cuota_fija_pat or 0.0,
                            #'analytic_distribution': credit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
                        _logger.info('cuota fija patronal cre')
                _logger.info('paso cuota fija')

                #Excedente SGM
                if self.tablas_id.pat_exedente_smg_deb:
                        debit_line = (0, 0, {
                            'name': 'Excedente SGM',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_exedente_smg_deb.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_exedente_smg > 0.0 and slip.pat_exedente_smg or 0.0,
                            'credit': slip.pat_exedente_smg < 0.0 and -slip.pat_exedente_smg or 0.0,
                            #'analytic_distribution': debit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if self.tablas_id.pat_cuota_fija_pat_cre:
                        credit_line = (0, 0, {
                            'name': 'Excedente SGM',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_exedente_smg_cre.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_exedente_smg < 0.0 and -slip.pat_exedente_smg or 0.0,
                            'credit': slip.pat_exedente_smg > 0.0 and slip.pat_exedente_smg or 0.0,
                            #'analytic_distribution': credit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                #Prestamo dinero
                if self.tablas_id.pat_prest_dinero_deb:
                        debit_line = (0, 0, {
                            'name': 'Excedente SGM',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_prest_dinero_deb.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_prest_dinero > 0.0 and slip.pat_prest_dinero or 0.0,
                            'credit': slip.pat_prest_dinero < 0.0 and -slip.pat_prest_dinero or 0.0,
                            #'analytic_distribution': debit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if self.tablas_id.pat_prest_dinero_cre:
                        credit_line = (0, 0, {
                            'name': 'Excedente SGM',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_prest_dinero_cre.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_prest_dinero < 0.0 and -slip.pat_prest_dinero or 0.0,
                            'credit': slip.pat_prest_dinero > 0.0 and slip.pat_prest_dinero or 0.0,
                            #'analytic_distribution': credit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                #Gastos medicos
                if self.tablas_id.pat_esp_pens_deb:
                        debit_line = (0, 0, {
                            'name': 'Gastos medicos',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_esp_pens_deb.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_esp_pens > 0.0 and slip.pat_esp_pens or 0.0,
                            'credit': slip.pat_esp_pens < 0.0 and -slip.pat_esp_pens or 0.0,
                            #'analytic_distribution': debit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if self.tablas_id.pat_esp_pens_cre:
                        credit_line = (0, 0, {
                            'name': 'Gastos medicos',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_esp_pens_cre.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_esp_pens < 0.0 and -slip.pat_esp_pens or 0.0,
                            'credit': slip.pat_esp_pens > 0.0 and slip.pat_esp_pens or 0.0,
                            #'analytic_distribution': credit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                #Riesgo de trabajo
                if self.tablas_id.pat_riesgo_trabajo_deb:
                        debit_line = (0, 0, {
                            'name': 'Riesgo de trabajo',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_riesgo_trabajo_deb.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_riesgo_trabajo > 0.0 and slip.pat_riesgo_trabajo or 0.0,
                            'credit': slip.pat_riesgo_trabajo < 0.0 and -slip.pat_riesgo_trabajo or 0.0,
                            #'analytic_distribution': debit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if self.tablas_id.pat_riesgo_trabajo_cre:
                        credit_line = (0, 0, {
                            'name': 'Riesgo de trabajo',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_riesgo_trabajo_cre.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_riesgo_trabajo < 0.0 and -slip.pat_riesgo_trabajo or 0.0,
                            'credit': slip.pat_riesgo_trabajo > 0.0 and slip.pat_riesgo_trabajo or 0.0,
                            #'analytic_distribution': credit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                #Invalidez y Vida
                if self.tablas_id.pat_invalidez_vida_deb:
                        debit_line = (0, 0, {
                            'name': 'Invalidez y Vida',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_invalidez_vida_deb.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_invalidez_vida > 0.0 and slip.pat_invalidez_vida or 0.0,
                            'credit': slip.pat_invalidez_vida < 0.0 and -slip.pat_invalidez_vida or 0.0,
                            #'analytic_distribution': debit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if self.tablas_id.pat_invalidez_vida_cre:
                        credit_line = (0, 0, {
                            'name': 'Invalidez y Vida',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_invalidez_vida_cre.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_invalidez_vida < 0.0 and -slip.pat_invalidez_vida or 0.0,
                            'credit': slip.pat_invalidez_vida > 0.0 and slip.pat_invalidez_vida or 0.0,
                            #'analytic_distribution': credit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                #Guarderias y PS
                if self.tablas_id.pat_guarderias_deb:
                        debit_line = (0, 0, {
                            'name': 'Guarderias y PS',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_guarderias_deb.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_guarderias > 0.0 and slip.pat_guarderias or 0.0,
                            'credit': slip.pat_guarderias < 0.0 and -slip.pat_guarderias or 0.0,
                            #'analytic_distribution': debit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if self.tablas_id.pat_guarderias_cre:
                        credit_line = (0, 0, {
                            'name': 'Guarderias y PS',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_guarderias_cre.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_guarderias < 0.0 and -slip.pat_guarderias or 0.0,
                            'credit': slip.pat_guarderias > 0.0 and slip.pat_guarderias or 0.0,
                            #'analytic_distribution': credit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                #Guarderias y PS
                if self.tablas_id.pat_retiro_deb:
                        debit_line = (0, 0, {
                            'name': 'Guarderias y PS',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_retiro_deb.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_retiro > 0.0 and slip.pat_retiro or 0.0,
                            'credit': slip.pat_retiro < 0.0 and -slip.pat_retiro or 0.0,
                            #'analytic_distribution': debit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if self.tablas_id.pat_retiro_cre:
                        credit_line = (0, 0, {
                            'name': 'Guarderias y PS',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_retiro_cre.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_retiro < 0.0 and -slip.pat_retiro or 0.0,
                            'credit': slip.pat_retiro > 0.0 and slip.pat_retiro or 0.0,
                            #'analytic_distribution': credit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                #Cesantia y Vejez
                if self.tablas_id.pat_cesantia_vejez_deb:
                        debit_line = (0, 0, {
                            'name': 'Cesantia y Vejez',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_cesantia_vejez_deb.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_cesantia_vejez > 0.0 and slip.pat_cesantia_vejez or 0.0,
                            'credit': slip.pat_cesantia_vejez < 0.0 and -slip.pat_cesantia_vejez or 0.0,
                            #'analytic_distribution': debit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if self.tablas_id.pat_cesantia_vejez_cre:
                        credit_line = (0, 0, {
                            'name': 'Cesantia y Vejez',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_cesantia_vejez_cre.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_cesantia_vejez < 0.0 and -slip.pat_cesantia_vejez or 0.0,
                            'credit': slip.pat_cesantia_vejez > 0.0 and slip.pat_cesantia_vejez or 0.0,
                            #'analytic_distribution': credit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                #INFONAVIT
                if self.tablas_id.pat_infonavit_deb:
                        debit_line = (0, 0, {
                            'name': 'INFONAVIT',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_infonavit_deb.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_infonavit > 0.0 and slip.pat_infonavit or 0.0,
                            'credit': slip.pat_infonavit < 0.0 and -slip.pat_infonavit or 0.0,
                            #'analytic_distribution': debit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if self.tablas_id.pat_infonavit_cre:
                        credit_line = (0, 0, {
                            'name': 'INFONAVIT',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_infonavit_cre.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_infonavit < 0.0 and -slip.pat_infonavit or 0.0,
                            'credit': slip.pat_infonavit > 0.0 and slip.pat_infonavit or 0.0,
                            #'analytic_distribution': credit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                #IMSS Patron
                if self.tablas_id.pat_total_deb:
                        debit_line = (0, 0, {
                            'name': 'IMSS Patron',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_total_deb.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_total > 0.0 and slip.pat_total or 0.0,
                            'credit': slip.pat_total < 0.0 and -slip.pat_total or 0.0,
                            #'analytic_distribution': debit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if self.tablas_id.pat_total_cre:
                        credit_line = (0, 0, {
                            'name': 'IMSS Patron',
                            'partner_id': slip.employee_id.address_home_id.id or '',
                            'account_id': self.tablas_id.pat_total_cre.id,
                            'journal_id': self.journal_id.id,
                            'date': date,
                            'debit': slip.pat_total < 0.0 and -slip.pat_total or 0.0,
                            'credit': slip.pat_total > 0.0 and slip.pat_total or 0.0,
                            #'analytic_distribution': credit_analytic_account_id,
                            #'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                if currency.compare_amounts(credit_sum, debit_sum) == -1:
                    acc_id = slip.journal_id.default_account_id.id
                    if not acc_id:
                        raise UserError(_('El diario de gasto "%s" no tiene configurado la cuenta de crédito') % (self.journal_id.name))
                    adjust_credit = (0, 0, {
                        'name': _('Entrada de ajuste'),
                        'partner_id': False,
                        'account_id': acc_id,
                        'journal_id': self.journal_id.id,
                        'date': date,
                        'debit': 0.0,
                        'credit': currency.round(debit_sum - credit_sum),
                    })
                    line_ids.append(adjust_credit)

                elif currency.compare_amounts(debit_sum, credit_sum) == -1:
                    acc_id = slip.journal_id.default_account_id.id
                    if not acc_id:
                        raise UserError(_('El diario de gasto "%s" no tiene configurado la cuenta de débito') % (self.journal_id.name))
                    adjust_debit = (0, 0, {
                        'name': _('Entrada de ajuste'),
                        'partner_id': False,
                        'account_id': acc_id,
                        'journal_id': self.journal_id.id,
                        'date': date,
                        'debit': currency.round(credit_sum - debit_sum),
                        'credit': 0.0,
                    })
                    line_ids.append(adjust_debit)

                move_dict['line_ids'] = line_ids
                move = self.env['account.move'].create(move_dict)
                slip.write({'move_id': move.id, 'date': date})
                move.action_post()
       return True
