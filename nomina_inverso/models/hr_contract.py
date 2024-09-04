# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
from .WhatIfAnalysis import GoalSeek
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class Contract(models.Model):
    _inherit = "hr.contract"

    sbc_fijo = fields.Float('SBC calculo inverso')
    acum_per_grav  = fields.Float('Percepciones gravadas')
    acum_isr  = fields.Float('ISR')
    acum_isr_antes_subem  = fields.Float('ISR antes de SUBEM')
    acum_subsidio_aplicado  = fields.Float('Subsidio aplicado')
    ultima_nomina = fields.Boolean(string="Ultima nomina del mes")

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

    def compute_sueldo_neto(self, monto):
       goal=monto

       # (iii) Define a starting point
       x0 = monto / 30

       ## Here is the result
       result = GoalSeek(self.calculo_inverso,goal,x0)
       _logger.info('Result is %s', result)
       self.wage = round(result * 30, 2)

       if self.sbc_fijo:
            values = {
             'sueldo_diario': round(result, 2),
             'sueldo_hora': self.wage/30/8,
             'sueldo_diario_integrado': self.sbc_fijo,
             'sueldo_base_cotizacion': self.sbc_fijo,
            }
            self.update(values)
       else:
          self._compute_sueldo()

       self.env['contract.historial.salario'].create({'sueldo_mensual': self.wage, 'sueldo_diario': self.sueldo_diario, 'fecha_sueldo':  date.today(),
                                                                   'sueldo_por_hora' : self.sueldo_hora, 'sueldo_diario_integrado': self.sueldo_diario_integrado,
                                                                   'sueldo_base_cotizacion': self.sueldo_base_cotizacion, 'contract_id' : self.id
                                                                   })

    def compute_factor(self, sueldo_diario): 
        if self.date_start: 
            #odoo 12
            today = datetime.today().date()
            diff_date = (today - self.date_start + timedelta(days=1)).days
            years = diff_date /365.0
            #date_start = datetime.strptime(self.date_start, "%Y-%m-%d") 
            #today = datetime.today() 
            #diff_date = today - date_start + timedelta(days=1)
            #years = diff_date.days /365.0
            #_logger.info('years ... %s', years)
            if not self.tablas_cfdi_id:
                 raise UserError(_('El contrato no cuenta con una tabla CFDI configurada.'))
            tablas_cfdi = self.tablas_cfdi_id 
            if not tablas_cfdi: 
                tablas_cfdi = self.env['tablas.cfdi'].search([],limit=1) 
            if not tablas_cfdi:
                return 
            if years < 1.0: 
                tablas_cfdi_lines = tablas_cfdi.tabla_antiguedades.filtered(lambda x: x.antiguedad >= years).sorted(key=lambda x:x.antiguedad) 
            else: 
                tablas_cfdi_lines = tablas_cfdi.tabla_antiguedades.filtered(lambda x: x.antiguedad <= years).sorted(key=lambda x:x.antiguedad, reverse=True) 
            if not tablas_cfdi_lines: 
                return 
            tablas_cfdi_line = tablas_cfdi_lines[0]

            _logger.info('years %s', years)
            _logger.info('tablas_cfdi_line.aguinaldo %s', tablas_cfdi_line.aguinaldo)
            _logger.info('tablas_cfdi_line.vacaciones %s', tablas_cfdi_line.vacaciones)
            _logger.info('tablas_cfdi_line.prima_vac %s', tablas_cfdi_line.prima_vac)

            factor = ((365 + tablas_cfdi_line.aguinaldo + (tablas_cfdi_line.vacaciones)* (tablas_cfdi_line.prima_vac/100) ) / 365 )
        else: 
            factor = 0
        return factor

    def calculo_inverso(self, sueldo_diario):

       factor = self.compute_factor(sueldo_diario)
       _logger.info('factor %s', factor)
       if self.sbc_fijo:
          sueldo_base_cotizacion = self.sbc_fijo
       else:
          sueldo_base_cotizacion = sueldo_diario * factor
       _logger.info('sueldo_base_cotizacion %s', sueldo_base_cotizacion)

       max_sbc = self.tablas_cfdi_id .uma * 25
       if sueldo_base_cotizacion > max_sbc:
          sueldo_base_cotizacion = max_sbc
       _logger.info('sueldo_base_cotizacion %s', sueldo_base_cotizacion)

       #percepciones
       percepciones_total = self.compute_percepciones(sueldo_diario)
       _logger.info('percepciones_total %s', percepciones_total)
       monto_exento = self.compute_monto_exento(sueldo_diario)
       percepciones_gravadas = percepciones_total - monto_exento
       _logger.info('precepciones gravadas %s', percepciones_gravadas)
       _logger.info('monto_exento %s', monto_exento)

       #otros pagos
       total_otros = 0
       subsidio_amount = self.compute_subsidio(percepciones_gravadas)
       total_otros += subsidio_amount
       _logger.info('subsidio_amount %s', subsidio_amount)
       if self.ultima_nomina:
           isr_ret_x_subsidio_entregado = self.compute_isr_ret_x_subsidio_entregado(percepciones_gravadas)
           total_otros += isr_ret_x_subsidio_entregado
           _logger.info('isr_ret_x_subsidio_entregado %s', isr_ret_x_subsidio_entregado)

           devolucion_subem_entregado = self.compute_devolucion_subem_entregado(percepciones_gravadas)
           total_otros += devolucion_subem_entregado
           _logger.info('devolucion_subem_entregado %s', devolucion_subem_entregado)

           devolucion_isr = self.compute_devolucion_isr(percepciones_gravadas)
           total_otros += devolucion_isr
           _logger.info('devolucion_isr %s', devolucion_isr)

       #deducciones
       total_deducciones = 0
       isr_amount = self.compute_isr(percepciones_gravadas)
       _logger.info('isr_amount %s', isr_amount)
       total_deducciones += isr_amount

       imss_amount = self.compute_imss(sueldo_base_cotizacion, sueldo_diario)
       _logger.info('imss_amount %s', imss_amount)
       total_deducciones += imss_amount

       if self.ultima_nomina:
           isr_ajuste = self.compute_isr_ajuste(percepciones_gravadas)
           total_deducciones += isr_ajuste
           _logger.info('isr_ajuste %s', isr_ajuste)

           ajuste_subsidio_entregado = self.compute_ajuste_subsidio_entregado(percepciones_gravadas)
           total_deducciones += ajuste_subsidio_entregado
           _logger.info('ajuste_subsidio_entregado %s', ajuste_subsidio_entregado)

           ajuste_subsidio_causado = self.compute_ajuste_subsidio_causado(percepciones_gravadas)
           total_deducciones += ajuste_subsidio_causado
           _logger.info('ajuste_subsidio_causado %s', ajuste_subsidio_causado)

       _logger.info('total_deducciones %s', total_deducciones)
       sueldo_neto = percepciones_total + total_otros - total_deducciones
       _logger.info('sueldo neto %s', sueldo_neto)

       return sueldo_neto

    def compute_percepciones(self, sueldo_diario):
       #leer tablas
       sueldo_periodo = 0
       dias_pagar = 0
       dias_sept = 0
       sueldo_sept = 0
       total_percepciones = 0

       #dias laborados
       if self.periodicidad_pago == '02':
            if self.sept_dia:
               dias_pagar =  6
               dias_sept = 1
            else:
               dias_pagar =  7
       elif self.periodicidad_pago == '04':
            dias_pagar =  15

       if dias_pagar == 0:
          raise UserError(_('Se debe configurar un periodo semanal o quincenal para realizar el cálculo.'))

       total_percepciones = sueldo_diario * dias_pagar
       total_percepciones += sueldo_diario * dias_sept

       if self.bono_productividad:
          total_percepciones += (sueldo_diario * dias_pagar) * self.bono_productividad_amount / 100
       if self.bono_asistencia:
          total_percepciones += (sueldo_diario * dias_pagar) * self.bono_asistencia_amount / 100
       if self.bono_puntualidad:
          total_percepciones += (sueldo_diario * dias_pagar) * self.bono_puntualidad_amount / 100
       if self.vale_despensa:
          total_percepciones += (sueldo_diario * dias_pagar) * self.vale_despensa_amount / 100
       if self.alimentacion:
          total_percepciones += (sueldo_diario * dias_pagar) * self.alimentacion_amount / 100

       estrategia_fiscal = False
       if estrategia_fiscal:
          if self.date_start: 
            #odoo 12
            today = datetime.today().date()
            diff_date = (today - self.date_start + timedelta(days=1)).days
            years = diff_date /365.0
            #date_start = datetime.strptime(self.date_start, "%Y-%m-%d") 
            #today = datetime.today() 
            #diff_date = today - date_start + timedelta(days=1)
            #years = diff_date.days /365.0
            #_logger.info('years ... %s', years)
            tablas_cfdi = self.tablas_cfdi_id 
            if not tablas_cfdi: 
                tablas_cfdi = self.env['tablas.cfdi'].search([],limit=1) 
            if not tablas_cfdi:
                return 
            if years < 1.0: 
                tablas_cfdi_lines = tablas_cfdi.tabla_antiguedades.filtered(lambda x: x.antiguedad >= years).sorted(key=lambda x:x.antiguedad) 
            else: 
                tablas_cfdi_lines = tablas_cfdi.tabla_antiguedades.filtered(lambda x: x.antiguedad <= years).sorted(key=lambda x:x.antiguedad, reverse=True) 
            if not tablas_cfdi_lines: 
                return 
            tablas_cfdi_line = tablas_cfdi_lines[0]
            #sumar vacaciones
            total_percepciones += (sueldo_diario * dias_pagar) * tablas_cfdi_line.vacaciones / 365
            _logger.info('vacaciones %s', (sueldo_diario * dias_pagar) * tablas_cfdi_line.vacaciones / 365)
            #sumar prima vacacional
            total_percepciones += ((sueldo_diario * dias_pagar) * tablas_cfdi_line.vacaciones / 365) * (tablas_cfdi_line.prima_vac/100)
            _logger.info('prima vacacional %s', ((sueldo_diario * dias_pagar) * tablas_cfdi_line.vacaciones / 365) * (tablas_cfdi_line.prima_vac/100))
            #sumar aguinaldo
            total_percepciones += (sueldo_diario * dias_pagar) * tablas_cfdi_line.aguinaldo / 365
            _logger.info('aguinaldo %s', (sueldo_diario * dias_pagar) * tablas_cfdi_line.aguinaldo / 365)

       return total_percepciones

    def compute_monto_exento(self, sueldo_diario):
       #leer tablas
       sueldo_periodo = 0
       dias_pagar = 0
       dias_sept = 0
       sueldo_sept = 0
       total_exento = 0

       #dias laborados
       if self.periodicidad_pago == '02':
            if self.sept_dia:
               dias_pagar =  6
               dias_sept = 1
            else:
               dias_pagar =  7
       elif self.periodicidad_pago == '04':
            dias_pagar =  15

       if dias_pagar == 0:
          raise UserError(_('Se debe configurar un periodo semanal o quincenal para realizar el cálculo.'))

       if self.vale_despensa:
          monto_vale = (sueldo_diario * dias_pagar) * self.vale_despensa_amount / 100
          monto_exento = self.tablas_cfdi_id.uma * self.tablas_cfdi_id.imss_mes
          if monto_vale > monto_exento:
              total_exento = monto_exento
          else:
              total_exento = monto_vale

       estrategia_fiscal = False
       if estrategia_fiscal:
          if self.date_start: 
            #odoo 12
            today = datetime.today().date()
            diff_date = (today - self.date_start + timedelta(days=1)).days
            years = diff_date /365.0
            #date_start = datetime.strptime(self.date_start, "%Y-%m-%d") 
            #today = datetime.today() 
            #diff_date = today - date_start + timedelta(days=1)
            #years = diff_date.days /365.0
            #_logger.info('years ... %s', years)
            tablas_cfdi = self.tablas_cfdi_id 
            if not tablas_cfdi: 
                tablas_cfdi = self.env['tablas.cfdi'].search([],limit=1) 
            if not tablas_cfdi:
                return 
            if years < 1.0: 
                tablas_cfdi_lines = tablas_cfdi.tabla_antiguedades.filtered(lambda x: x.antiguedad >= years).sorted(key=lambda x:x.antiguedad) 
            else: 
                tablas_cfdi_lines = tablas_cfdi.tabla_antiguedades.filtered(lambda x: x.antiguedad <= years).sorted(key=lambda x:x.antiguedad, reverse=True) 
            if not tablas_cfdi_lines: 
                return 
            tablas_cfdi_line = tablas_cfdi_lines[0]
            #sumar prima vacacional
            total_exento += ((sueldo_diario * dias_pagar) * tablas_cfdi_line.vacaciones / 365) * (tablas_cfdi_line.prima_vac/100)
            #sumar aguinaldo
            total_exento += (sueldo_diario * dias_pagar) * tablas_cfdi_line.aguinaldo / 365

       return total_exento

    def compute_subsidio(self, percepciones_gravadas):
       #leer tablas
       limite_inferior = 0
       cuota_fija = 0
       porcentaje_sobre_excedente = 0
       subsidio_empleo = 0
       dias_pagar = 0
       grabado_mensual = 0
       grabado_subsidio = 0
       dias_periodo = 0

       #dias laborados
       if self.periodicidad_pago == '02':
            dias_pagar =  7
       elif self.periodicidad_pago == '04':
            dias_pagar =  15
       if dias_pagar == 0:
          raise UserError(_('Se debe configurar un periodo semanal o quincenal para realizar el cálculo.'))

       #grabado_mensual
       if self.ultima_nomina:
          grabado_mensual = percepciones_gravadas + self.acum_per_grav
          grabado_subsidio = percepciones_gravadas + self.acum_per_grav
          if self.tablas_cfdi_id:
             line = self.env['tablas.general.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)
       else:
          grabado_mensual = percepciones_gravadas
          grabado_subsidio = percepciones_gravadas / dias_pagar * self.tablas_cfdi_id.imss_mes
          if self.tablas_cfdi_id:
             line = self.env['tablas.isr.periodo'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)

       if line:
           limite_inferior = line.lim_inf
           cuota_fija = line.c_fija
           porcentaje_sobre_excedente = line.s_excedente
       line2 = self.env['tablas.subsidio.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_subsidio)],order='lim_inf desc',limit=1)
       if line2:
           subsidio_empleo = line2.s_mensual

       #articulo 113
       excedente_limite_superior = grabado_mensual - limite_inferior
       impuesto_marginal = excedente_limite_superior * porcentaje_sobre_excedente/100
       isr_tarifa_113 = impuesto_marginal + cuota_fija

       subem_entregar = 0
       factor01 = 0
       dev_isr = 0
       #subsidio mensual
       if self.ultima_nomina:
          if subsidio_empleo > isr_tarifa_113:
             if subsidio_empleo - isr_tarifa_113  < self.acum_isr or (subsidio_empleo > isr_tarifa_113 and self.acum_isr > 0):
                 dev_isr = self.acum_isr
             subem_entregar = subsidio_empleo - isr_tarifa_113
             factor01 = self.acum_isr_antes_subem + subem_entregar - self.acum_subsidio_aplicado - dev_isr
             if factor01 > 0:
                subem_entregar = factor01
             else:
                subem_entregar = 0
       else:
          subsidio_pagado = isr_tarifa_113 - (subsidio_empleo / self.tablas_cfdi_id.imss_mes) * dias_pagar
          total = isr_tarifa_113
          total2 =  subsidio_pagado

       result = 0
       if self.ultima_nomina:
          if subem_entregar > 0:
             result = subem_entregar
          else:
             result = 0
       else:
          if subsidio_empleo > 0:
             if subsidio_pagado < 0:
                result = abs(total2)
             else:
                result = 0
          else:
             result = 0
       return result

    def compute_isr(self, percepciones_gravadas):
       #leer tablas
       limite_inferior = 0
       cuota_fija = 0
       porcentaje_sobre_excedente = 0
       subsidio_empleo = 0
       dias_pagar = 0
       grabado_mensual = 0
       grabado_subsidio = 0
       dias_periodo = 0

       #dias laborados
       if self.periodicidad_pago == '02':
            dias_pagar =  7
       elif self.periodicidad_pago == '04':
            dias_pagar =  15
       if dias_pagar == 0:
          raise UserError(_('Se debe configurar un periodo semanal o quincenal para realizar el cálculo.'))

       #grabado_mensual
       if self.ultima_nomina:
          grabado_mensual = percepciones_gravadas + self.acum_per_grav
          grabado_subsidio = percepciones_gravadas + self.acum_per_grav
          if self.tablas_cfdi_id:
             line = self.env['tablas.general.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)
       else:
          grabado_mensual = percepciones_gravadas
          grabado_subsidio = percepciones_gravadas / dias_pagar * self.tablas_cfdi_id.imss_mes
          if self.tablas_cfdi_id:
             line = self.env['tablas.isr.periodo'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)

       if line:
           limite_inferior = line.lim_inf
           cuota_fija = line.c_fija
           porcentaje_sobre_excedente = line.s_excedente
       line2 = self.env['tablas.subsidio.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_subsidio)],order='lim_inf desc',limit=1)
       if line2:
           subsidio_empleo = line2.s_mensual

       #articulo 113
       excedente_limite_superior = grabado_mensual - limite_inferior
       impuesto_marginal = excedente_limite_superior * porcentaje_sobre_excedente/100
       isr_tarifa_113 = impuesto_marginal + cuota_fija

       op_isr_ajuste = 0
       isr_retener = 0

       #subsidio mensual
       if self.ultima_nomina:
          isr_retener = isr_tarifa_113 - subsidio_empleo
          isr_retener = isr_retener - self.acum_isr
          if self.acum_subsidio_aplicado > 0 and subsidio_empleo == 0:
              if subsidio_empleo == 0:
                 if self.acum_subsidio_aplicado > self.acum_isr_antes_subem:
                    op_isr_ajuste = self.acum_isr_antes_subem
                 else:
                    op_isr_ajuste = self.acum_subsidio_aplicado
                 isr_retener = isr_retener - op_isr_ajuste
              else:
                 isr_retener = isr_retener - self.acum_isr_antes_subem + self.acum_subsidio_aplicado
          else:
              if self.acum_subsidio_aplicado > subsidio_empleo:
                 isr_retener = isr_retener - (self.acum_subsidio_aplicado - subsidio_empleo)
       else:
          subsidio_pagado = isr_tarifa_113 - (subsidio_empleo / self.tablas_cfdi_id.imss_mes) * dias_pagar
          total = isr_tarifa_113
          total2 =  subsidio_pagado

       result = 0
       if self.ultima_nomina:
            if isr_retener < 0:
                result =  0
            else:
                result = isr_retener
       else:
            if subsidio_pagado < 0:
                result =  0
            else:
                if total2 < 0:
                   result = abs(total)
                else:
                   result =abs(total2)
       return result

    def compute_imss(self, sueldosbc, sueldodiario):
        #cuota del IMSS parte del Empleado
        dias_laborados = 0
        dias_completos = 0
        dias_falta = 0
        dias_trabajo = 0
        monto_sbc = sueldosbc

        if self.periodicidad_pago == '02':
            dias_completos = 7
            dias_laborados =  7
            dias_falta = 7
        elif self.periodicidad_pago == '04':
            dias_completos = 15
            dias_laborados =  15
            dias_falta = 15

        if self.periodicidad_pago != '02' and self.periodicidad_pago != '04':
          raise UserError(_('Se debe configurar un periodo semanal o quincenal para realizar el cálculo.'))

        #salario_cotizado = self.sueldo_base_cotizacion
        base_calculo = 0
        base_execente = 0
        if monto_sbc < 25 * self.tablas_cfdi_id.uma:
            base_calculo = monto_sbc
        else:
            base_calculo = 25 * self.tablas_cfdi_id.uma

        if base_calculo > 3 * self.tablas_cfdi_id.uma:
            base_execente = base_calculo - 3 * self.tablas_cfdi_id.uma

        if sueldodiario <= self.tablas_cfdi_id.salario_minimo:
           calcular_imss = False
        else:
           calcular_imss = True
        #imss empleado
        emp_total = 0

        #imss patronal
        pat_total = 0

        if calcular_imss:
            #imss empleado
            emp_exedente_smg = round(dias_completos * self.tablas_cfdi_id.enf_mat_excedente_e/100 * base_execente,2)
            emp_prest_dinero = round(dias_completos * self.tablas_cfdi_id.enf_mat_prestaciones_e/100 * base_calculo,2)
            emp_esp_pens = round(dias_completos * self.tablas_cfdi_id.enf_mat_gastos_med_e/100 * base_calculo,2)
            emp_invalidez_vida = round(dias_laborados * self.tablas_cfdi_id.inv_vida_e/100 * base_calculo,2)
            emp_cesantia_vejez = round(dias_laborados * self.tablas_cfdi_id.cesantia_vejez_e/100 * base_calculo,2)
            emp_total = emp_exedente_smg + emp_prest_dinero + emp_esp_pens + emp_invalidez_vida + emp_cesantia_vejez
            
            #imss patronal
            factor_riesgo = 0
            if self.riesgo_puesto == '1':
                factor_riesgo = self.tablas_cfdi_id.rt_clase1
            elif self.riesgo_puesto == '2':
                factor_riesgo = self.tablas_cfdi_id.rt_clase2
            elif self.riesgo_puesto == '3':
                factor_riesgo = self.tablas_cfdi_id.rt_clase3
            elif self.riesgo_puesto == '4':
                factor_riesgo = self.tablas_cfdi_id.rt_clase4
            elif self.riesgo_puesto == '5':
                factor_riesgo = self.tablas_cfdi_id.rt_clase5
            pat_cuota_fija_pat = round(dias_completos * self.tablas_cfdi_id.enf_mat_cuota_fija/100 * self.tablas_cfdi_id.uma,2)
            pat_exedente_smg =round(dias_completos * self.tablas_cfdi_id.enf_mat_excedente_p/100 * base_execente,2)
            pat_prest_dinero = round(dias_completos * self.tablas_cfdi_id.enf_mat_prestaciones_p/100 * base_calculo,2)
            pat_esp_pens = round(dias_completos * self.tablas_cfdi_id.enf_mat_gastos_med_p/100 * base_calculo,2)
            pat_riesgo_trabajo = round(dias_laborados * factor_riesgo/100 * base_calculo,2) # falta
            pat_invalidez_vida = round(dias_laborados * self.tablas_cfdi_id.inv_vida_p/100 * base_calculo,2)
            pat_guarderias = round(dias_laborados * self.tablas_cfdi_id.guarderia_p/100 * base_calculo,2)
            pat_retiro = round(dias_falta * self.tablas_cfdi_id.retiro_p/100 * base_calculo,2)
            pat_cesantia_vejez = round(dias_laborados * self.tablas_cfdi_id.cesantia_vejez_p/100 * base_calculo,2)
            pat_infonavit = round(dias_falta * self.tablas_cfdi_id.apotacion_infonavit/100 * base_calculo,2)
            pat_total = pat_cuota_fija_pat + pat_exedente_smg + pat_prest_dinero + pat_esp_pens + pat_riesgo_trabajo + pat_invalidez_vida + pat_guarderias + pat_retiro + pat_cesantia_vejez + pat_infonavit

        return emp_total

    def update_values(self, ultima_nomina, mes):
        self.ultima_nomina = ultima_nomina
        _logger.info('ultima nomina %s', self.ultima_nomina)
        if self.ultima_nomina:
           self.mes = mes
           self._get_acumulados_mensual()
        else:
           self.acum_subsidio_aplicado = 0
           self.acum_isr_antes_subem = 0
           self.acum_per_grav = 0
           self.acum_isr = 0

    def acumulado_mes(self, codigo):
        total = 0
        if self.employee_id and self.tablas_cfdi_id:
            mes_actual = self.tablas_cfdi_id.tabla_mensual.search([('mes', '=', self.mes),('form_id', '=', self.tablas_cfdi_id.id)],limit =1)

            date_start = mes_actual.dia_inicio # self.date_from
            date_end = mes_actual.dia_fin #self.date_to
            domain=[('state','=', 'done')]
            if date_start:
                domain.append(('date_from','>=',date_start))
            if date_end:
                domain.append(('date_to','<=',date_end))
            domain.append(('employee_id','=',self.employee_id.id))
            rules = self.env['hr.salary.rule'].search([('code', '=', codigo)])
            payslips = self.env['hr.payslip'].search(domain)
            for nomina in payslips:
                _logger.info('nomina %s', nomina.number)
            payslip_lines = payslips.mapped('line_ids').filtered(lambda x: x.salary_rule_id.id in rules.ids)
            employees = {}
            for line in payslip_lines:
                if line.slip_id.employee_id not in employees:
                    employees[line.slip_id.employee_id] = {line.slip_id: []}
                if line.slip_id not in employees[line.slip_id.employee_id]:
                    employees[line.slip_id.employee_id].update({line.slip_id: []})
                employees[line.slip_id.employee_id][line.slip_id].append(line)

            for employee, payslips in employees.items():
                for payslip,lines in payslips.items():
                    for line in lines:
                        total += line.total
        return total

    def _get_acumulados_mensual(self):
         self.acum_subsidio_aplicado = self.acumulado_mes('SUB')
         _logger.info('acum_subsidio_aplicado %s', self.acum_subsidio_aplicado)
         self.acum_isr_antes_subem = self.acumulado_mes('ISR')
         _logger.info('acum_isr_antes_subem %s', self.acum_isr_antes_subem)
         self.acum_per_grav = self.acumulado_mes('TPERG')
         _logger.info('acum_per_grav %s', self.acum_per_grav)
         self.acum_isr = self.acumulado_mes('ISR2')
         _logger.info('acum_isr %s', self.acum_isr)

    def compute_isr_ret_x_subsidio_entregado(self, percepciones_gravadas):
       #leer tablas
       limite_inferior = 0
       cuota_fija = 0
       porcentaje_sobre_excedente = 0
       subsidio_empleo = 0
       dias_pagar = 0
       grabado_mensual = 0
       grabado_subsidio = 0
       dias_periodo = 0

       #dias laborados
       if self.periodicidad_pago == '02':
            dias_pagar =  7
       elif self.periodicidad_pago == '04':
            dias_pagar =  15
       #periodo = self.env['tablas.periodo.mensual'].search([('form_id','=',self.tablas_cfdi_id.id),('dia_fin','>=',datetime.today()),('dia_inicio','<=',datetime.today())],limit=1)
       #dias_periodo = dias_pagar

       #grabado_mensual
       if self.ultima_nomina:
          grabado_mensual = percepciones_gravadas + self.acum_per_grav
          grabado_subsidio = percepciones_gravadas + self.acum_per_grav
          if self.tablas_cfdi_id:
             line = self.env['tablas.general.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)
       else:
          grabado_mensual = percepciones_gravadas
          grabado_subsidio = percepciones_gravadas / dias_pagar * self.tablas_cfdi_id.imss_mes
          if self.tablas_cfdi_id:
             line = self.env['tablas.isr.periodo'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)

       if line:
           limite_inferior = line.lim_inf
           cuota_fija = line.c_fija
           porcentaje_sobre_excedente = line.s_excedente
       line2 = self.env['tablas.subsidio.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_subsidio)],order='lim_inf desc',limit=1)
       if line2:
           subsidio_empleo = line2.s_mensual

       #articulo 113
       excedente_limite_superior = grabado_mensual - limite_inferior
       impuesto_marginal = excedente_limite_superior * porcentaje_sobre_excedente/100
       isr_tarifa_113 = impuesto_marginal + cuota_fija

       #subsidio mensual
       subsidio_pagado = isr_tarifa_113 - (subsidio_empleo / self.tablas_cfdi_id.imss_mes) * dias_pagar
       total = isr_tarifa_113
       total2 =  subsidio_pagado

       op_isr_ajuste = 0
       op_ajuste_subem_causado = 0
       op_ajuste_subem = 0
       desc_dev_isr = 0
       desc_isr_ret_subem_entregado = 0
       desc_dev_subem = 0
       subem_entregar =  0
       factor01 = 0
       isr_retener = 0
       result = 0

       if isr_tarifa_113 > subsidio_empleo:
           isr_retener = isr_tarifa_113 - subsidio_empleo
           isr_retener = isr_retener - self.acum_isr
           if self.acum_subsidio_aplicado > 0 and subsidio_empleo == 0:
               if self.acum_subsidio_aplicado > self.acum_isr_antes_subem:
                  desc_isr_ret_subem_entregado = self.acum_isr_antes_subem
                  desc_dev_subem = self.acum_subsidio_aplicado - self.acum_isr_antes_subem
               else:
                  desc_isr_ret_subem_entregado = self.acum_subsidio_aplicado
               if subsidio_empleo == 0:
                  if self.acum_subsidio_aplicado > self.acum_isr_antes_subem:
                     op_isr_ajuste = self.acum_isr_antes_subem
                  else:
                     op_isr_ajuste = self.acum_subsidio_aplicado
                  if self.acum_subsidio_aplicado > 0:
                     op_ajuste_subem_causado =  self.acum_subsidio_aplicado
           else:
              result = 0
       else:
           subem_entregar = subsidio_empleo - isr_tarifa_113
           if self.acum_isr_antes_subem > self.acum_subsidio_aplicado:
              factor01 = self.acum_isr_antes_subem
           else:
              factor01 = self.acum_subsidio_aplicado
           subem_entregar = factor01 - self.acum_isr_antes_subem - subem_entregar

       return desc_isr_ret_subem_entregado

    def compute_devolucion_subem_entregado(self, percepciones_gravadas):
       #leer tablas
       limite_inferior = 0
       cuota_fija = 0
       porcentaje_sobre_excedente = 0
       subsidio_empleo = 0
       dias_pagar = 0
       grabado_mensual = 0
       grabado_subsidio = 0
       dias_periodo = 0

       #dias laborados
       if self.periodicidad_pago == '02':
            dias_pagar =  7
       elif self.periodicidad_pago == '04':
            dias_pagar =  15
       #periodo = self.env['tablas.periodo.mensual'].search([('form_id','=',self.tablas_cfdi_id.id),('dia_fin','>=',datetime.today()),('dia_inicio','<=',datetime.today())],limit=1)
       #dias_periodo = dias_pagar

       #grabado_mensual
       if self.ultima_nomina:
          grabado_mensual = percepciones_gravadas + self.acum_per_grav
          grabado_subsidio = percepciones_gravadas + self.acum_per_grav
          if self.tablas_cfdi_id:
             line = self.env['tablas.general.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)
       else:
          grabado_mensual = percepciones_gravadas
          grabado_subsidio = percepciones_gravadas / dias_pagar * self.tablas_cfdi_id.imss_mes
          if self.tablas_cfdi_id:
             line = self.env['tablas.isr.periodo'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)

       if line:
           limite_inferior = line.lim_inf
           cuota_fija = line.c_fija
           porcentaje_sobre_excedente = line.s_excedente
       line2 = self.env['tablas.subsidio.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_subsidio)],order='lim_inf desc',limit=1)
       if line2:
           subsidio_empleo = line2.s_mensual

       #articulo 113
       excedente_limite_superior = grabado_mensual - limite_inferior
       impuesto_marginal = excedente_limite_superior * porcentaje_sobre_excedente/100
       isr_tarifa_113 = impuesto_marginal + cuota_fija

       #subsidio mensual
       subsidio_pagado = isr_tarifa_113 - (subsidio_empleo / self.tablas_cfdi_id.imss_mes) * dias_pagar
       total = isr_tarifa_113
       total2 =  subsidio_pagado

       op_isr_ajuste = 0
       op_ajuste_subem_causado = 0
       op_ajuste_subem = 0
       desc_dev_isr = 0
       desc_isr_ret_subem_entregado = 0
       desc_dev_subem = 0
       subem_entregar =  0
       factor01 = 0
       isr_retener = 0
       result = 0

       if isr_tarifa_113 > subsidio_empleo:
           isr_retener = isr_tarifa_113 - subsidio_empleo
           isr_retener = isr_retener - self.acum_isr
           if self.acum_subsidio_aplicado > 0 and subsidio_empleo == 0:
               if self.acum_subsidio_aplicado > self.acum_isr_antes_subem:
                  desc_isr_ret_subem_entregado = self.acum_isr_antes_subem
                  desc_dev_subem = self.acum_subsidio_aplicado - self.acum_isr_antes_subem
               else:
                  desc_isr_ret_subem_entregado = self.acum_subsidio_aplicado
               if subsidio_empleo == 0:
                  if self.acum_subsidio_aplicado > self.acum_isr_antes_subem:
                     op_isr_ajuste = self.acum_isr_antes_subem
                  else:
                     op_isr_ajuste = self.acum_subsidio_aplicado
                  if self.acum_subsidio_aplicado > 0:
                     op_ajuste_subem_causado =  self.acum_subsidio_aplicado
           else:
              result = 0
       else:
           subem_entregar = subsidio_empleo - isr_tarifa_113
           if self.acum_isr_antes_subem > self.acum_subsidio_aplicado:
              factor01 = self.acum_isr_antes_subem
           else:
              factor01 = self.acum_subsidio_aplicado
           subem_entregar = factor01 - self.acum_isr_antes_subem - subem_entregar

       return desc_dev_subem

    def compute_devolucion_isr(self, percepciones_gravadas):
       #leer tablas
       limite_inferior = 0
       cuota_fija = 0
       porcentaje_sobre_excedente = 0
       subsidio_empleo = 0
       dias_pagar = 0
       grabado_mensual = 0
       grabado_subsidio = 0
       dias_periodo = 0

       #dias laborados
       if self.periodicidad_pago == '02':
            dias_pagar =  7
       elif self.periodicidad_pago == '04':
            dias_pagar =  15
       #periodo = self.env['tablas.periodo.mensual'].search([('form_id','=',self.tablas_cfdi_id.id),('dia_fin','>=',datetime.today()),('dia_inicio','<=',datetime.today())],limit=1)
       #dias_periodo = dias_pagar

       #grabado_mensual
       if self.ultima_nomina:
          grabado_mensual = percepciones_gravadas + self.acum_per_grav
          grabado_subsidio = percepciones_gravadas + self.acum_per_grav
          if self.tablas_cfdi_id:
             line = self.env['tablas.general.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)
       else:
          grabado_mensual = percepciones_gravadas
          grabado_subsidio = percepciones_gravadas / dias_pagar * self.tablas_cfdi_id.imss_mes
          if self.tablas_cfdi_id:
             line = self.env['tablas.isr.periodo'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)

       if line:
           limite_inferior = line.lim_inf
           cuota_fija = line.c_fija
           porcentaje_sobre_excedente = line.s_excedente
       line2 = self.env['tablas.subsidio.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_subsidio)],order='lim_inf desc',limit=1)
       if line2:
           subsidio_empleo = line2.s_mensual

       #articulo 113
       excedente_limite_superior = grabado_mensual - limite_inferior
       impuesto_marginal = excedente_limite_superior * porcentaje_sobre_excedente/100
       isr_tarifa_113 = impuesto_marginal + cuota_fija

       #subsidio mensual
       subsidio_pagado = isr_tarifa_113 - (subsidio_empleo / self.tablas_cfdi_id.imss_mes) * dias_pagar
       total = isr_tarifa_113
       total2 =  subsidio_pagado

       op_isr_ajuste = 0
       op_ajuste_subem_causado = 0
       op_ajuste_subem = 0
       desc_dev_isr = 0
       desc_isr_ret_subem_entregado = 0
       desc_dev_subem = 0
       subem_entregar =  0
       factor01 = 0
       isr_retener = 0
       result = 0

       if isr_tarifa_113 > subsidio_empleo:
           isr_retener = isr_tarifa_113 - subsidio_empleo
           isr_retener = isr_retener - self.acum_isr
           if self.acum_subsidio_aplicado > 0 and subsidio_empleo == 0:
               if self.acum_subsidio_aplicado > self.acum_isr_antes_subem:
                  desc_isr_ret_subem_entregado = self.acum_isr_antes_subem
                  desc_dev_subem = self.acum_subsidio_aplicado - self.acum_isr_antes_subem
               else:
                  desc_isr_ret_subem_entregado = self.acum_subsidio_aplicado
               if subsidio_empleo == 0:
                  if self.acum_subsidio_aplicado > self.acum_isr_antes_subem:
                     op_isr_ajuste = self.acum_isr_antes_subem
                  else:
                     op_isr_ajuste = self.acum_subsidio_aplicado
                  if self.acum_subsidio_aplicado > 0:
                     op_ajuste_subem_causado =  self.acum_subsidio_aplicado
           else:
              result = 0
       else:
           if subsidio_empleo - isr_tarifa_113  < self.acum_isr:
               subem_entregar = self.acum_isr

       if isr_retener - op_isr_ajuste < 0 or subem_entregar > 0 or (subsidio_empleo > isr_tarifa_113 and self.acum_isr > 0):
           if isr_retener - op_isr_ajuste < 0: 
              return abs(isr_retener - op_isr_ajuste)
           else:
              return abs(subem_entregar)
       else:
           return 0

    def compute_isr_ajuste(self, percepciones_gravadas):
       #leer tablas
       limite_inferior = 0
       cuota_fija = 0
       porcentaje_sobre_excedente = 0
       subsidio_empleo = 0
       dias_pagar = 0
       grabado_mensual = 0
       grabado_subsidio = 0
       dias_periodo = 0

       #dias laborados
       if self.periodicidad_pago == '02':
            dias_pagar =  7
       elif self.periodicidad_pago == '04':
            dias_pagar =  15
       #periodo = self.env['tablas.periodo.mensual'].search([('form_id','=',self.tablas_cfdi_id.id),('dia_fin','>=',datetime.today()),('dia_inicio','<=',datetime.today())],limit=1)
       #dias_periodo = dias_pagar

       #grabado_mensual
       if self.ultima_nomina:
          grabado_mensual = percepciones_gravadas + self.acum_per_grav
          grabado_subsidio = percepciones_gravadas + self.acum_per_grav
          if self.tablas_cfdi_id:
             line = self.env['tablas.general.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)
       else:
          grabado_mensual = percepciones_gravadas
          grabado_subsidio = percepciones_gravadas / dias_pagar * self.tablas_cfdi_id.imss_mes
          if self.tablas_cfdi_id:
             line = self.env['tablas.isr.periodo'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)

       if line:
           limite_inferior = line.lim_inf
           cuota_fija = line.c_fija
           porcentaje_sobre_excedente = line.s_excedente
       line2 = self.env['tablas.subsidio.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_subsidio)],order='lim_inf desc',limit=1)
       if line2:
           subsidio_empleo = line2.s_mensual

       #articulo 113
       excedente_limite_superior = grabado_mensual - limite_inferior
       impuesto_marginal = excedente_limite_superior * porcentaje_sobre_excedente/100
       isr_tarifa_113 = impuesto_marginal + cuota_fija

       #subsidio mensual
       subsidio_pagado = isr_tarifa_113 - (subsidio_empleo / self.tablas_cfdi_id.imss_mes) * dias_pagar
       total = isr_tarifa_113
       total2 =  subsidio_pagado

       op_isr_ajuste = 0
       op_ajuste_subem_causado = 0
       op_ajuste_subem = 0
       desc_dev_isr = 0
       desc_isr_ret_subem_entregado = 0
       desc_dev_subem = 0
       subem_entregar =  0
       factor01 = 0
       isr_retener = 0
       result = 0

       if isr_tarifa_113 > subsidio_empleo:
           isr_retener = isr_tarifa_113 - subsidio_empleo
           isr_retener = isr_retener - self.acum_isr
           if self.acum_subsidio_aplicado > 0 and subsidio_empleo == 0:
               if self.acum_subsidio_aplicado > self.acum_isr_antes_subem:
                  desc_isr_ret_subem_entregado = self.acum_isr_antes_subem
                  desc_dev_subem = self.acum_subsidio_aplicado - self.acum_isr_antes_subem
               else:
                  desc_isr_ret_subem_entregado = self.acum_subsidio_aplicado
               if subsidio_empleo == 0:
                  if self.acum_subsidio_aplicado > self.acum_isr_antes_subem:
                     op_isr_ajuste = self.acum_isr_antes_subem
                  else:
                     op_isr_ajuste = self.acum_subsidio_aplicado
                  if self.acum_subsidio_aplicado > 0:
                     op_ajuste_subem_causado =  self.acum_subsidio_aplicado
           else:
              result = 0
       else:
           subem_entregar = subsidio_empleo - isr_tarifa_113
           if self.acum_isr_antes_subem > self.acum_subsidio_aplicado:
              factor01 = self.acum_isr_antes_subem
           else:
              factor01 = self.acum_subsidio_aplicado
           subem_entregar = factor01 - self.acum_isr_antes_subem - subem_entregar

       return op_isr_ajuste

    def compute_ajuste_subsidio_entregado(self, percepciones_gravadas):
       #leer tablas
       limite_inferior = 0
       cuota_fija = 0
       porcentaje_sobre_excedente = 0
       subsidio_empleo = 0
       dias_pagar = 0
       grabado_mensual = 0
       grabado_subsidio = 0
       dias_periodo = 0

       #dias laborados
       if self.periodicidad_pago == '02':
            dias_pagar =  7
       elif self.periodicidad_pago == '04':
            dias_pagar =  15
       #periodo = self.env['tablas.periodo.mensual'].search([('form_id','=',self.tablas_cfdi_id.id),('dia_fin','>=',datetime.today()),('dia_inicio','<=',datetime.today())],limit=1)
       #dias_periodo = dias_pagar

       #grabado_mensual
       if self.ultima_nomina:
          grabado_mensual = percepciones_gravadas + self.acum_per_grav
          grabado_subsidio = percepciones_gravadas + self.acum_per_grav
          if self.tablas_cfdi_id:
             line = self.env['tablas.general.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)
       else:
          grabado_mensual = percepciones_gravadas
          grabado_subsidio = percepciones_gravadas / dias_pagar * self.tablas_cfdi_id.imss_mes
          if self.tablas_cfdi_id:
             line = self.env['tablas.isr.periodo'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)

       if line:
           limite_inferior = line.lim_inf
           cuota_fija = line.c_fija
           porcentaje_sobre_excedente = line.s_excedente
       line2 = self.env['tablas.subsidio.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_subsidio)],order='lim_inf desc',limit=1)
       if line2:
           subsidio_empleo = line2.s_mensual

       #articulo 113
       excedente_limite_superior = grabado_mensual - limite_inferior
       impuesto_marginal = excedente_limite_superior * porcentaje_sobre_excedente/100
       isr_tarifa_113 = impuesto_marginal + cuota_fija

       #subsidio mensual
       subsidio_pagado = isr_tarifa_113 - (subsidio_empleo / self.tablas_cfdi_id.imss_mes) * dias_pagar
       total = isr_tarifa_113
       total2 =  subsidio_pagado

       op_isr_ajuste = 0
       op_ajuste_subem_causado = 0
       op_ajuste_subem = 0
       desc_dev_isr = 0
       desc_isr_ret_subem_entregado = 0
       desc_dev_subem = 0
       subem_entregar =  0
       factor01 = 0
       isr_retener = 0
       result = 0

       if isr_tarifa_113 > subsidio_empleo:
           if self.acum_subsidio_aplicado > self.acum_isr_antes_subem:
              op_ajuste_subem = self.acum_subsidio_aplicado - self.acum_isr_antes_subem
       else:
           subem_entregar = subsidio_empleo - isr_tarifa_113
           if self.acum_isr_antes_subem > self.acum_subsidio_aplicado:
              factor01 = self.acum_isr_antes_subem
           else:
              factor01 = self.acum_subsidio_aplicado
           subem_entregar = factor01 - self.acum_isr_antes_subem - subem_entregar

       if op_ajuste_subem > 0 or subem_entregar > 0: 
           if op_ajuste_subem > 0:
              return op_ajuste_subem
           else:
              return subem_entregar
       else:
           return 0

    def compute_ajuste_subsidio_causado(self, percepciones_gravadas):
       #leer tablas
       limite_inferior = 0
       cuota_fija = 0
       porcentaje_sobre_excedente = 0
       subsidio_empleo = 0
       dias_pagar = 0
       grabado_mensual = 0
       grabado_subsidio = 0
       dias_periodo = 0

       #dias laborados
       if self.periodicidad_pago == '02':
            dias_pagar =  7
       elif self.periodicidad_pago == '04':
            dias_pagar =  15
       #periodo = self.env['tablas.periodo.mensual'].search([('form_id','=',self.tablas_cfdi_id.id),('dia_fin','>=',datetime.today()),('dia_inicio','<=',datetime.today())],limit=1)
       #dias_periodo = dias_pagar

       #grabado_mensual
       if self.ultima_nomina:
          grabado_mensual = percepciones_gravadas + self.acum_per_grav
          grabado_subsidio = percepciones_gravadas + self.acum_per_grav
          if self.tablas_cfdi_id:
             line = self.env['tablas.general.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)
       else:
          grabado_mensual = percepciones_gravadas
          grabado_subsidio = percepciones_gravadas / dias_pagar * self.tablas_cfdi_id.imss_mes
          if self.tablas_cfdi_id:
             line = self.env['tablas.isr.periodo'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_mensual)],order='lim_inf desc',limit=1)

       if line:
           limite_inferior = line.lim_inf
           cuota_fija = line.c_fija
           porcentaje_sobre_excedente = line.s_excedente
       line2 = self.env['tablas.subsidio.line'].search([('form_id','=',self.tablas_cfdi_id.id),('lim_inf','<=',grabado_subsidio)],order='lim_inf desc',limit=1)
       if line2:
           subsidio_empleo = line2.s_mensual

       #articulo 113
       excedente_limite_superior = grabado_mensual - limite_inferior
       impuesto_marginal = excedente_limite_superior * porcentaje_sobre_excedente/100
       isr_tarifa_113 = impuesto_marginal + cuota_fija

       #subsidio mensual
       subsidio_pagado = isr_tarifa_113 - (subsidio_empleo / self.tablas_cfdi_id.imss_mes) * dias_pagar
       total = isr_tarifa_113
       total2 =  subsidio_pagado

       op_isr_ajuste = 0
       op_ajuste_subem_causado = 0
       op_ajuste_subem = 0
       desc_dev_isr = 0
       desc_isr_ret_subem_entregado = 0
       desc_dev_subem = 0
       subem_entregar =  0
       factor01 = 0
       isr_retener = 0
       result = 0

       if isr_tarifa_113 > subsidio_empleo:
           isr_retener = isr_tarifa_113 - subsidio_empleo
           isr_retener = isr_retener - self.acum_isr
           if self.acum_subsidio_aplicado > 0 and subsidio_empleo == 0:
               if self.acum_subsidio_aplicado > self.acum_isr_antes_subem:
                  desc_isr_ret_subem_entregado = self.acum_isr_antes_subem
                  desc_dev_subem = self.acum_subsidio_aplicado - self.acum_isr_antes_subem
               else:
                  desc_isr_ret_subem_entregado = self.acum_subsidio_aplicado
               if subsidio_empleo == 0:
                  if self.acum_subsidio_aplicado > self.acum_isr_antes_subem:
                     op_isr_ajuste = self.acum_isr_antes_subem
                  else:
                     op_isr_ajuste = self.acum_subsidio_aplicado
                  if self.acum_subsidio_aplicado > 0:
                     op_ajuste_subem_causado =  self.acum_subsidio_aplicado
           else:
              result = 0
       else:
           subem_entregar = subsidio_empleo - isr_tarifa_113
           if self.acum_isr_antes_subem > self.acum_subsidio_aplicado:
              factor01 = self.acum_isr_antes_subem
           else:
              factor01 = self.acum_subsidio_aplicado
           subem_entregar = factor01 - self.acum_isr_antes_subem - subem_entregar

       return op_ajuste_subem_causado

