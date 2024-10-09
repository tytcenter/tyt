#-*- coding:utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero

class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    def _get_partner_id(self, credit_account):
        """
        Get partner_id of slip line to use in account_move_line
        """
        # use partner of salary rule or fallback on employee's address
        partner_id = self.slip_id.employee_id.address_home_id.id
        if credit_account:
            if self.salary_rule_id.account_credit.account_type in ('asset_receivable', 'liability_payable'):
                return partner_id
        else:
            if self.salary_rule_id.account_debit.account_type in ('asset_receivable', 'liability_payable'):
                return partner_id
        return False

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    date = fields.Date('Date Account', states={'draft': [('readonly', False)]}, readonly=True,
        help="Keep empty to use the period of the validation(Payslip) date.")
    journal_id = fields.Many2one('account.journal', 'Salary Journal', readonly=True, required=True,
        states={'draft': [('readonly', False)]}, default=lambda self: self.env['account.journal'].search([('type', '=', 'general')], limit=1))
    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        if 'journal_id' in self.env.context:
            for vals in vals_list:
                vals['journal_id'] = self.env.context.get('journal_id')
        return super(HrPayslip, self).create(vals_list)

    @api.onchange('contract_id')
    def onchange_contract(self):
        super(HrPayslip, self).onchange_contract()
        self.journal_id = self.contract_id.journal_id.id or (not self.contract_id and self.default_get(['journal_id'])['journal_id'])

    def action_payslip_cancel(self):
        moves = self.mapped('move_id')
        moves.filtered(lambda x: x.state == 'posted').button_cancel()
        #moves.unlink()
        return super(HrPayslip, self).action_payslip_cancel()

    def action_payslip_done(self):
        tipo_de_poliza = self.env['ir.config_parameter'].sudo().get_param('om_hr_payroll_account_ee.tipo_de_poliza')
        if tipo_de_poliza=='Por nómina':
            return super(HrPayslip, self).action_payslip_done()
        else:
            res = super(HrPayslip, self).action_payslip_done()

            for slip in self:
                if slip.total_nom == 0:
                  continue
                if slip.move_id:
                  continue
                line_ids = []
                debit_sum = 0.0
                credit_sum = 0.0
                date = slip.date or slip.date_to
                currency = slip.company_id.currency_id

                name = _('Nómina de %s') % (slip.employee_id.name)
                move_dict = {
                    'narration': name,
                    'ref': slip.number,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                }
                for line in slip.details_by_salary_rule_category:
                    amount = currency.round(line.total)
                    if currency.is_zero(amount):
                        continue
                    debit_account_id = line.salary_rule_id.account_debit.id
                    credit_account_id = line.salary_rule_id.account_credit.id

                    #obtener la cuenta analitica de crédito
                    if slip.contract_id.analytic_distribution:
                       credit_analytic_account_id = slip.contract_id.analytic_distribution
                    else:
                       credit_analytic_account_id = None
                    if not credit_analytic_account_id and line.salary_rule_id.analytic_distribution:
                       credit_analytic_account_id = line.salary_rule_id.analytic_distribution

                    #obtener la cuenta analitica de debito
                    if slip.contract_id.analytic_distribution:
                       debit_analytic_account_id = slip.contract_id.analytic_distribution
                    else:
                       debit_analytic_account_id = None
                    if not debit_analytic_account_id and line.salary_rule_id.analytic_distribution:
                       debit_analytic_account_id = line.salary_rule_id.analytic_distribution

                    department_id = slip.employee_id.contract_id and slip.employee_id.contract_id.department_id and slip.employee_id.contract_id.department_id.id or False
                    #obtener la cuenta de debito
                    debit_account_id = False
                    if department_id:
                        deudoras = line.salary_rule_id.cta_deudora_ids.filtered(lambda x:x.department_id.id==department_id and x.account_credit)
                        if deudoras:
                            debit_account_id = deudoras[0].account_credit.id
                            if deudoras[0].account_analytic and not debit_analytic_account_id:
                                debit_analytic_account_id = deudoras[0].account_analytic.id
                    if not debit_account_id:
                        debit_account_id = line.salary_rule_id.account_debit.id

                    #obtener la cuenta de crédito
                    credit_account_id = False
                    if department_id:
                        contabilidads = line.salary_rule_id.cta_acreedora_ids.filtered(lambda x:x.department_id.id==department_id and x.account_credit)
                        if contabilidads:
                            credit_account_id = contabilidads[0].account_credit.id
                            if contabilidads[0].account_analytic and not credit_analytic_account_id:
                               credit_analytic_account_id = contabilidads[0].account_analytic.id
                    if not credit_account_id:
                        credit_account_id = line.salary_rule_id.account_credit.id

                    if debit_account_id:
                        debit_line = (0, 0, {
                            'name': line.name,
                            'partner_id': line._get_partner_id(credit_account=False),
                            'account_id': debit_account_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': amount > 0.0 and amount or 0.0,
                            'credit': amount < 0.0 and -amount or 0.0,
                            'analytic_distribution': debit_analytic_account_id,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                    if credit_account_id:
                        credit_line = (0, 0, {
                            'name': line.name,
                            'partner_id': line._get_partner_id(credit_account=True),
                            'account_id': credit_account_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': amount < 0.0 and -amount or 0.0,
                            'credit': amount > 0.0 and amount or 0.0,
                            'analytic_distribution': credit_analytic_account_id,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                if currency.compare_amounts(credit_sum, debit_sum) == -1:
                    acc_id = slip.journal_id.default_account_id.id
                    if not acc_id:
                        raise UserError(_('El diario de gasto "%s" no tiene configurado la cuenta de crédito') % (slip.journal_id.name))
                    adjust_credit = (0, 0, {
                        'name': _('Entrada de ajuste'),
                        'partner_id': False,
                        'account_id': acc_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': 0.0,
                        'credit': currency.round(debit_sum - credit_sum),
                    })
                    line_ids.append(adjust_credit)

                elif currency.compare_amounts(debit_sum, credit_sum) == -1:
                    acc_id = slip.journal_id.default_account_id.id
                    if not acc_id:
                        raise UserError(_('El diario de gasto "%s" no tiene configurado la cuenta de débito') % (slip.journal_id.name))
                    adjust_debit = (0, 0, {
                        'name': _('Entrada de ajuste'),
                        'partner_id': False,
                        'account_id': acc_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': currency.round(credit_sum - debit_sum),
                        'credit': 0.0,
                    })
                    line_ids.append(adjust_debit)
                move_dict['line_ids'] = line_ids
                move = self.env['account.move'].create(move_dict)
                slip.write({'move_id': move.id, 'date': date})
                move.action_post()
            return res

class HrSalaryRule(models.Model):
    _inherit = ['hr.salary.rule', 'analytic.mixin']
    _name = 'hr.salary.rule'

    account_tax_id = fields.Many2one('account.tax', 'Cuenta de Impuesto')
    account_debit = fields.Many2one('account.account', 'Cuenta débito', domain=[('deprecated', '=', False)])
    account_credit = fields.Many2one('account.account', 'Cuenta crédito', domain=[('deprecated', '=', False)])
    cta_deudora_ids = fields.One2many('nomina.deudora', 'doc_id', 'cta_deudora')
    cta_acreedora_ids = fields.One2many('nomina.acreedora', 'doc_id', 'cta_acreedora')


class HrContract(models.Model):
    _inherit = ['hr.contract', 'analytic.mixin']
    _description = 'Employee Contract'
    _name = "hr.contract"

    #analytic_distribution = fields.Json(inverse="_inverse_analytic_distribution", 'Cuenta analítica')
    journal_id = fields.Many2one('account.journal', 'Diario de nómina')

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    journal_id = fields.Many2one('account.journal', 'Diario de nómina', states={'draft': [('readonly', False)]}, readonly=True,
        required=True, default=lambda self: self.env['account.journal'].search([('type', '=', 'general')], limit=1))
    is_all_payslip_done = fields.Boolean("¿Están todas la nóminas hechas?", compute='_compute_is_all_payslip_done')
    move_id = fields.Many2one('account.move', 'Asiento contable', readonly=True, copy=False)

    def _compute_is_all_payslip_done(self):
        tipo_de_poliza = self.env['ir.config_parameter'].sudo().get_param('om_hr_payroll_account_ee.tipo_de_poliza')
        for batch in self:
            if tipo_de_poliza != 'Por nómina':
                batch.is_all_payslip_done = False
            else:    
                statuses = batch.slip_ids.mapped('state')
                if len(set(statuses))==1 and statuses[0]=='done':
                    batch.is_all_payslip_done = True
                else: 
                    batch.is_all_payslip_done = False

    def action_crear_poliza(self):
        precision = self.env['decimal.precision'].precision_get('Payroll')
        payslip_obj = self.env['hr.payslip']
        for slip_batch in self:
            slips_confirm = slip_batch.slip_ids.filtered(lambda x:x.state in ['draft', 'waiting'])
            if slips_confirm:
                slips_confirm.action_payslip_done()
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            date = slip_batch.date_end
            currency = slip_batch.journal_id.company_id.currency_id

            slip_batch_journal_id = slip_batch.journal_id.id
            name = _('Procesamiento de nomina %s') % (slip_batch.name)
            move_dict = {
                'narration': name,
                'ref': slip_batch.name,
                'journal_id': slip_batch_journal_id,
                'date': date,
            }
            payslips = payslip_obj.browse()
            for slip in slip_batch.slip_ids:
                if slip.move_id:
                    continue
                if slip.state != 'done':
                  continue
                for line in slip.details_by_salary_rule_category:
                    amount = currency.round(line.total)
                    if currency.is_zero(amount): #float_is_zero(amount, precision_digits=precision):
                        continue

                    department_id = slip.employee_id.contract_id and slip.employee_id.contract_id.department_id and slip.employee_id.contract_id.department_id.id or False
                    #obtener la cuenta de debito
                    if slip.contract_id.analytic_distribution:
                       debit_analytic_account_id = slip.contract_id.analytic_distribution
                    else:
                       debit_analytic_account_id = None
                    debit_account_id = False
                    if department_id:
                        deudoras = line.salary_rule_id.cta_deudora_ids.filtered(lambda x:x.department_id.id==department_id and x.account_credit)
                        if deudoras:
                            debit_account_id = deudoras[0].account_credit.id
                            if deudoras[0].account_analytic and not debit_analytic_account_id:
                               debit_analytic_account_id = deudoras[0].account_analytic.id
                    if not debit_account_id:
                        debit_account_id = line.salary_rule_id.account_debit.id
                    if not debit_analytic_account_id and line.salary_rule_id.analytic_distribution:
                       debit_analytic_account_id = line.salary_rule_id.analytic_distribution

                    #obtener la cuenta de crédito
                    if slip.contract_id.analytic_distribution:
                       credit_analytic_account_id = slip.contract_id.analytic_distribution
                    else:
                       credit_analytic_account_id = None
                    credit_account_id = False
                    if department_id:
                        contabilidads = line.salary_rule_id.cta_acreedora_ids.filtered(lambda x:x.department_id.id==department_id and x.account_credit)
                        if contabilidads:
                            credit_account_id = contabilidads[0].account_credit.id
                            if contabilidads[0].account_analytic and not credit_analytic_account_id:
                               credit_analytic_account_id = contabilidads[0].account_analytic.id
                    if not credit_account_id:
                        credit_account_id = line.salary_rule_id.account_credit.id
                    if not credit_analytic_account_id and line.salary_rule_id.analytic_distribution:
                       credit_analytic_account_id = line.salary_rule_id.analytic_distribution

                    if debit_account_id:
                        debit_line = (0, 0, {
                            'name': line.name,
                            'partner_id': line._get_partner_id(credit_account=False),
                            'account_id': debit_account_id,
                            'journal_id': slip_batch_journal_id, #slip.journal_id.id,
                            'date': date,
                            'debit': amount > 0.0 and amount or 0.0,
                            'credit': amount < 0.0 and -amount or 0.0,
                            'analytic_distribution': debit_analytic_account_id,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                            'department_id': department_id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
    
                    if credit_account_id:
                        credit_line = (0, 0, {
                            'name': line.name,
                            'partner_id': line._get_partner_id(credit_account=True),
                            'account_id': credit_account_id,
                            'journal_id': slip_batch_journal_id, #slip.journal_id.id,
                            'date': date,
                            'debit': amount < 0.0 and -amount or 0.0,
                            'credit': amount > 0.0 and amount or 0.0,
                            'analytic_distribution': credit_analytic_account_id,
                            'tax_line_id': line.salary_rule_id.account_tax_id.id,
                            'department_id': department_id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
                payslips += slip

            if currency.compare_amounts(credit_sum, debit_sum) == -1:
                    acc_id = slip_batch.journal_id.default_account_id.id
                    if not acc_id:
                        raise UserError(_('El diario de gasto "%s" no tiene configurado la cuenta de crédito') % (slip_batch.journal_id.name))
                    adjust_credit = (0, 0, {
                        'name': _('Entrada de ajuste'),
                        'partner_id': False,
                        'account_id': acc_id,
                        'journal_id': slip_batch.journal_id.id,
                        'date': date,
                        'debit': 0.0,
                        'credit': currency.round(debit_sum - credit_sum),
                        'department_id': False,
                    })
                    line_ids.append(adjust_credit)
            elif currency.compare_amounts(debit_sum, credit_sum) == -1:
                    acc_id = slip_batch.journal_id.default_account_id.id
                    if not acc_id:
                        raise UserError(_('El diario de gasto "%s" no tiene configurado la cuenta de débito') % (slip_batch.journal_id.name))
                    adjust_debit = (0, 0, {
                        'name': _('Entrada de ajuste'),
                        'partner_id': False,
                        'account_id': acc_id,
                        'journal_id': slip_batch.journal_id.id,
                        'date': date,
                        'debit': currency.round(credit_sum - debit_sum),
                        'credit': 0.0,
                        'department_id': False,
                    })
                    line_ids.append(adjust_debit)

            tipo_de_poliza = self.env['ir.config_parameter'].sudo().get_param('om_hr_payroll_account_ee.tipo_de_poliza')
            compacta =  self.env['ir.config_parameter'].sudo().get_param('om_hr_payroll_account_ee.compacta')
            tipo_de_compacta =  self.env['ir.config_parameter'].sudo().get_param('om_hr_payroll_account_ee.tipo_de_compacta')
            new_dict = {}
            new_list = []
            items = []
            if tipo_de_poliza == 'Por nómina' and compacta == 'True':
                if tipo_de_compacta == '01':
                   for line in line_ids:
                       account_id = line[2].get('account_id')
                       new_list = line[2]
                       for key, val in new_dict.items():
                           if key == account_id:
                               credit = line[2].get('credit') + val.get('credit')
                               debit = line[2].get('debit') + val.get('debit')
                               new_list['credit'] = credit
                               new_list['debit'] = debit
                       new_dict.update({account_id: new_list})
                   for data,item in new_dict.items():
                       items.append((0, 0, item))
                   line_ids = items

                if tipo_de_compacta == '02':
                   for line in line_ids:
                       account_id = 'key' + str(line[2].get('account_id')) + str(line[2].get('department_id'))
                       new_list = line[2]
                       if line[2].get('department_id'):
                          dept_name = self.env['hr.department'].browse(line[2].get('department_id')).name
                       else:
                          dept_name = ''
                       new_list['name'] = line[2].get('name') + ' ' + dept_name
                       for key, val in new_dict.items():
                           if key == account_id:
                               credit = line[2].get('credit') + val.get('credit')
                               debit = line[2].get('debit') + val.get('debit')
                               new_list['credit'] = credit
                               new_list['debit'] = debit
                       new_dict.update({account_id: new_list})
                   for data,item in new_dict.items():
                       items.append((0, 0, item))
                   line_ids = items
            for line in line_ids:
                line[2].pop('department_id')
            if line_ids:
                move_dict['line_ids'] = line_ids
                move = self.env['account.move'].create(move_dict)
                slip_batch.write({'move_id': move.id})
                payslips.write({'move_id': move.id, 'date': date})
                move.action_post()
        return True

class ContabilidadNomina(models.Model):
    _name = "nomina.deudora"
    _description = 'Cuentas deudoras'

    doc_id = fields.Many2one('hr.salary.rule', 'Cuentas contables')
    department_id = fields.Many2one('hr.department', string='Departmento')
    account_credit = fields.Many2one('account.account', 'Cuenta contable', domain=[('deprecated', '=', False)])
    account_analytic = fields.Many2one('account.analytic.account', 'Cuenta analítica')

class ContabilidadNomina(models.Model):
    _name = "nomina.acreedora"
    _description = 'Cuentas accreedoras'

    doc_id = fields.Many2one('hr.salary.rule', 'Cuentas contables')
    department_id = fields.Many2one('hr.department', string='Departmento')
    account_credit = fields.Many2one('account.account', 'Cuenta contable', domain=[('deprecated', '=', False)])
    account_analytic = fields.Many2one('account.analytic.account', 'Cuenta analítica')

