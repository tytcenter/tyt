# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from datetime import datetime, date, time
from collections import defaultdict
from dateutil.relativedelta import relativedelta
import pytz
from odoo.osv import expression
from odoo.tools import format_date

import logging
_logger = logging.getLogger(__name__)

class HrPayslipEmployeesExt(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def _check_undefined_slots(self, work_entries, payslip_run):
        """
        Check if a time slot in the contract's calendar is not covered by a work entry
        """
        work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])
        for work_entry in work_entries:
            work_entries_by_contract[work_entry.contract_id] |= work_entry

        for contract, work_entries in work_entries_by_contract.items():
            if contract.work_entry_source != 'calendar':
                continue
            calendar_start = pytz.utc.localize(datetime.combine(max(contract.date_start, payslip_run.date_start), time.min))
            calendar_end = pytz.utc.localize(datetime.combine(min(contract.date_end or date.max, payslip_run.date_end), time.max))
            outside = contract.resource_calendar_id._attendance_intervals_batch(calendar_start, calendar_end)[False] - work_entries._to_intervals()
            if outside:
                time_intervals_str = "\n - ".join(['', *["%s -> %s" % (s[0], s[1]) for s in outside._items]])
                raise UserError(_("Some part of %s's calendar is not covered by any work entry. Please complete the schedule. Time intervals to look for:%s") % (contract.employee_id.name, time_intervals_str))

    def _filter_contracts(self, contracts):
        # Could be overriden to avoid having 2 'end of the year bonus' payslips, etc.
        return contracts

    def compute_sheet(self):
        payslips = self.env['hr.payslip']
        [data] = self.read()
        active_id = self.env.context.get('active_id')
        if active_id:
            [run_data] = self.env['hr.payslip.run'].browse(active_id).read(['date_start', 'date_end'])
        else:
            return
        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')
        if not data['employee_ids']:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))
        payslip_batch = self.env['hr.payslip.run'].browse(active_id)
        struct_id = payslip_batch.estructura and payslip_batch.estructura.id or False

        employees = self.env['hr.employee'].browse(data['employee_ids'])

        ##### Compute Work Entries - New way
        contracts = employees._get_contracts(payslip_batch.date_start, payslip_batch.date_end, states=['open', 'close']).filtered(lambda c: c.active)
        contracts.generate_work_entries(payslip_batch.date_start, payslip_batch.date_end)
        work_entries = self.env['hr.work.entry'].search([
            ('date_start', '<=', payslip_batch.date_end + relativedelta(days=1)),
            ('date_stop', '>=', payslip_batch.date_start + relativedelta(days=-1)),
            ('employee_id', 'in', employees.ids),
        ])
        self._check_undefined_slots(work_entries, payslip_batch)


#        if(self.structure_id.type_id.default_struct_id == self.structure_id):
        work_entries = work_entries.filtered(lambda work_entry: work_entry.state != 'validated')
        if work_entries._check_if_error():
                work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])

                for work_entry in work_entries.filtered(lambda w: w.state == 'conflict'):
                    work_entries_by_contract[work_entry.contract_id] |= work_entry

                for contract, work_entries in work_entries_by_contract.items():
                    conflicts = work_entries._to_intervals()
                    time_intervals_str = "\n - ".join(['', *["%s -> %s" % (s[0], s[1]) for s in conflicts._items]])
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Some work entries could not be validated.'),
                        'message': _('Time intervals to look for:%s', time_intervals_str),
                        'sticky': False,
                    }
                }

        #Add Other Inputs
        other_inputs = []
        for other in payslip_batch.tabla_otras_entradas:
            if other.descripcion and other.codigo: 
                other_inputs.append((0,0,{'name':other.descripcion, 'code': other.codigo, 'amount':other.monto}))

        ##### Compute Payslips old way
        for employee in self.env['hr.employee'].browse(data['employee_ids']):
            slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id, contract_id=False)
            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'struct_id': struct_id or slip_data['value'].get('struct_id'),
                'contract_id': slip_data['value'].get('contract_id'),
                'payslip_run_id': active_id,
                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
                'date_from': from_date,
                'date_to': to_date,
                'company_id': employee.company_id.id,
                #Added
                'tipo_nomina' : payslip_batch.tipo_nomina,
                'fecha_pago' : payslip_batch.fecha_pago,
                #'journal_id': payslip_batch.journal_id.id
            }
            if other_inputs and res.get('contract_id'):
                contract_id = res.get('contract_id')
                input_lines = list(other_inputs)
                for line in input_lines:
                    line[2].update({'contract_id':contract_id})
                #input_lines = map(lambda x: x[2].update({'contract_id':contract_id}),input_lines)
                res.update({'input_line_ids': input_lines,})

            if not slip_data['value'].get('contract_id'):
               raise UserError(_("El contrato de %s no está en el rango de fechas de la nomina o no está en proceso.") % (employee.name))

            #si está habilitado revisar si tiene todas las nominas del periodo
            employ_contract_id = self.env['hr.contract'].search([('id', '=', slip_data['value'].get('contract_id'))])
            no_slips = 0
            ultima_nomina =  False
            if payslip_batch.periodicidad_pago == '02' or payslip_batch.periodicidad_pago == '04':
                if payslip_batch.ultima_nomina and payslip_batch.mes:
                    line = self.env['tablas.periodo.mensual'].search([('form_id','=',employ_contract_id.tablas_cfdi_id.id),('mes','=',payslip_batch.mes)],limit=1)
                    domain=[('state','=', 'done')]
                    if line:
                        domain.append(('date_from','>=',line.dia_inicio))
                        domain.append(('date_to','<=',line.dia_fin))
                    domain.append(('employee_id','=',employee.id))
                    payslips = self.env['hr.payslip'].search(domain)
                    if payslips:
                        no_slips = len(payslips)
                        if payslip_batch.periodicidad_pago == '04':
                           if no_slips >= 1:
                               ultima_nomina =  True
                        if payslip_batch.periodicidad_pago == '02':
                            if line:
                                if line.no_dias == 28 and no_slips >= 3:
                                    ultima_nomina =  True
                                if line.no_dias == 35 and no_slips >= 4:
                                    ultima_nomina =  True
            else:
                ultima_nomina =  True

            res.update({'dias_pagar': payslip_batch.dias_pagar,
                            'imss_mes': payslip_batch.imss_mes,
                            'ultima_nomina': ultima_nomina,
                            'mes': payslip_batch.mes,
                            'isr_ajustar': payslip_batch.isr_ajustar,
                            'isr_anual': payslip_batch.isr_anual,
                            'periodicidad_pago': payslip_batch.periodicidad_pago,
                            'concepto_periodico': payslip_batch.concepto_periodico,})
            date_start_1 = employ_contract_id.date_start
            d_from_1 = fields.Date.from_string(from_date)
            d_to_1 = fields.Date.from_string(to_date)
            if date_start_1:
               if date_start_1> d_from_1:
                   imss_dias =  (to_date - date_start_1).days + 1
                   res.update({'imss_dias': imss_dias,
                            'dias_infonavit': imss_dias,})
               else:
                   res.update({'imss_dias': payslip_batch.imss_dias,})
            else:
               res.update({'imss_dias': payslip_batch.imss_dias,})

            #Compute caja ahorro
            other_inputsb = []
            caja = self.env['caja.nomina'].search([('employee_id','=',employee.id),('fecha_aplicacion','>=',from_date), ('fecha_aplicacion', '<=', to_date),('state','=','done')])
            if caja:
               for other in caja:
                  if other.descripcion and other.clave: 
                     other_inputsb.append((0,0,{'name':other.descripcion, 'code': other.clave, 'amount':other.importe, 'contract_id':employ_contract_id.id}))
                     res.update({'input_line_ids': other_inputsb,})

            #Compute days for attendance module
            module = self.env['ir.module.module'].sudo().search([('name','=','hr_attendance_sheet')])
            if module and module.state == 'installed':
               if payslip_batch.attendance_report:
                   asistencia_lines = payslip_batch.attendance_report.mapped('attendent_sheet_ids')
                   emp_line_exist = asistencia_lines.filtered(lambda x: x.employee_id.id==employee.id)
                   if emp_line_exist:
                        res.update({'worked_days_line_ids': [(0, 0, x) for x in emp_line_exist.create_worklines(slip_data['value'].get('worked_days_line_ids'))],})

            payslips += self.env['hr.payslip'].create(res)
        payslips.compute_sheet()

        return {'type': 'ir.actions.act_window_close'}
