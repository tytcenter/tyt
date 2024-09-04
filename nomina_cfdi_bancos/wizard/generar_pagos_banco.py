# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, date
import base64
import logging
_logger = logging.getLogger(__name__)

class GenerarPagosBanco(models.TransientModel):
    _name='generar.pagos.banco'
    _description = 'GenerarPagosBanco'

    #banco_id = fields.Many2one("res.bank",string='Banco')
    banco_rfc = fields.Selection(
        selection=[('BBA830831LJ2', 'BBVA Bancomer - Mixto'),
                   ('BBA830831LJ2_2', 'BBVA Bancomer - Solo BBVA'),
                   ('BMN930209927', 'Banorte'),
                   ('BSM970519DU8', 'Santander - Solo Santanter'),
                   ('BSM970519DU8_2', 'Santander - Mixto'),
                   ('BNM840515VB1', 'Banamex - Dispersión "C"'),
                   ('BNM840515VB1_2', 'Banamex - Dispersión "D"'),
                   ('BRM940216EQ6', 'Banregio'),
                   ('HMI950125KG8', 'HSBC'),
                   ('SIN9412025I4', 'Scotiabank'),
                   ('BII931004P61', 'Inbursa'),
                   ('BBA9407071E1', 'Banbajio'),],
        string=_('Banco de dispersión'),
    )
    dato1 = fields.Char("Código de pago")
    dato2 = fields.Char("Dato adicional 2")
    dato3 = fields.Char("Dato adicional 3")
    banamex_no_cliente = fields.Char("No. cliente")
    banamex_secuencia = fields.Char("Secuencia", default="1")
    banamex_descripcion = fields.Char("Descripción", default='Nomina')
    banamex_referencia = fields.Char("Referencia")
    banorte_numero = fields.Char("No. emisor asignado")
    bbva_referencia = fields.Char("Referencia (7 digitos)")
    bbva_no_contrato = fields.Char("No. contrato (10 digitos)")
    scotia_numero = fields.Char("Número de cliente")
    scotia_cuenta = fields.Char("Cuenta de cargo")
    scotia_referencia = fields.Char("Referencia")
    inbursa_cuenta = fields.Char("No. cuenta")
    bajio_afinidad = fields.Char("Grupo afinidad")

    file_content = fields.Binary("Archivo")
    diario_pago = fields.Many2one('account.journal', string='Cuenta de pago', domain=[('type', '=', 'bank')])
    fecha_dispersion = fields.Date("Fecha de dispersión")
    employee_type = fields.Selection(
        selection=[('01', 'Todos los empleados en el procesamiento'),
                   ('02', 'Empleados con mismo banco que la cuenta de dispersión'),
                   ('03', 'Empleados con diferente banco que la cuenta de dispersión'),],
        string=_('Empleados a dispersar'), default='01'
    )

    def action_print_generar_pagos(self):
        file_text = []
        ctx = self._context.copy()
        active_id = ctx.get('active_id')
        active_model = ctx.get('active_model')
        str_encabezado = []
        str_sumario = []
        num_registro = 1
        num_empleados = 0
        monto_total = 0
        if active_id and active_model=='hr.payslip.run':
            record = self.env[active_model].browse(active_id)
              ##################################################################################
              ###################################################################################
              #encabezados 
              ###################################################################################
              ###################################################################################
            if self.banco_rfc == 'BSM970519DU8' or self.banco_rfc == 'BSM970519DU8_2': # Santander
                  enc1 = '1'+ str(num_registro).rjust(5, '0') + 'E'
                  enc2 = datetime.now().strftime("%m%d%Y")
                  if self.diario_pago.bank_account_id.acc_number:
                     enc3 = self.diario_pago.bank_account_id.acc_number.ljust(16)
                  else:
                     enc3 = '                '
                  enc4 = self.fecha_dispersion.strftime("%m%d%Y")
                  str_encabezado.append((enc1)+(enc2)+(enc3)+(enc4))
                  num_registro += 1
            elif self.banco_rfc == 'BNM840515VB1': # Banamex "C"
                  #primer encabezado
                  enc11 = '1' #FIJO
                  if not self.banamex_no_cliente:
                     raise UserError(_('Falta el número de cliente Banamex.'))
                  enc12 = self.banamex_no_cliente.rjust(12, '0')
                  enc13 = self.fecha_dispersion.strftime('%d%m%y')
                  enc14 = self.banamex_secuencia.rjust(4, '0') #no. consecutivo del 1-99
                  enc15 = self.diario_pago.company_id.nombre_fiscal[0:36].ljust(36, ' ') # RAZON SOCIAL
                  enc16 = self.banamex_descripcion.ljust(20, ' ') #DESCRIPCION
                  enc17 = '05' if self.employee_type == '02' else '07' # Pago de nomina (Pagomatico) a cuentas Banamex
                  enc18 = '                                        ' # solo para ordenes de pago
                  enc19 = 'C' # version
                  enc20 = '00' #fijo
                  str_encabezado.append((enc11)+(enc12)+(enc13)+(enc14)+(enc15)+(enc16)+(enc17)+(enc18)+(enc19)+(enc20))
            elif self.banco_rfc == 'BNM840515VB1_2': # Banamex "D"
                  #primer encabezado
                  enc11 = '1' #FIJO
                  if not self.banamex_no_cliente:
                     raise UserError(_('Falta el número de cliente Banamex.'))
                  enc12 = self.banamex_no_cliente.rjust(12, '0')
                  enc13 = self.fecha_dispersion.strftime('%y%m%d')
                  enc14 = '0001' #no. consecutivo del 1-99
                  enc15 = self.diario_pago.company_id.nombre_fiscal[0:36].ljust(36, ' ') # RAZON SOCIAL
                  enc16 = self.banamex_descripcion.ljust(20, ' ') #DESCRIPCION
                  enc17 = '15' # FIJO
                  enc18 = 'D' # version de layout
                  enc19 = '01' #fijo              123456789012345678    12345678901234567890
                  str_encabezado.append((enc11)+(enc12)+(enc13)+(enc14)+(enc15)+(enc16)+(enc17)+(enc18)+(enc19))
            elif self.banco_rfc == 'SIN9412025I4': # Scotia bank
                  #primer encabezado
                  enc11 = 'EEHA' #FIJO
                  if not self.scotia_numero:
                     raise UserError(_('Falta el número de cliente Scotiabank.'))
                  enc12 = self.scotia_numero.rjust(5, '0')
                  enc13 = "01000000000000000000000000000"
                  enc14 = '                                                                                                                                                                                                                                                                                                                                            '
                  enc16 = 'EEHB'
                  if not self.scotia_cuenta:
                     raise UserError(_('Falta el número de cuenta de cargo Scotiabank.'))
                  enc17 = self.scotia_cuenta.rjust(17, '0')
                  enc18 = "0000000001000"
                  enc19 = '                                                                                                                                                                                                                                                                                                                                                '
                  str_encabezado.append((enc11)+(enc12)+(enc13)+(enc14))
                  str_encabezado.append((enc16)+(enc17)+(enc18)+(enc19))
            elif self.banco_rfc == 'BBA9407071E1': # Banbajio
                  enc1 = '010000001030S900'
                  if not self.bajio_afinidad:
                     raise UserError(_('Falta el grupo afinidad.'))
                  enc2 = self.bajio_afinidad.rjust(7,'0')
                  enc3 = datetime.now().strftime("%Y%m%d")
                  if self.diario_pago.bank_account_id.acc_number:
                     enc4 = self.diario_pago.bank_account_id.acc_number.rjust(20,'0')
                  else:
                     enc4 = '                    '
                  enc5 = '                                                                                                                                  '
                  num_registro += 1
                  str_encabezado.append((enc1)+(enc2)+(enc3)+(enc4)+(enc5))

              ##################################################################################
              ###################################################################################
              #registos de detalle
              ###################################################################################
              ###################################################################################
            for payslip in record.slip_ids.filtered(lambda x: x.state!='cancel'):
                    employee = payslip.employee_id

                    if employee.tipo_pago=='transferencia' and employee.diario_pago.bank_id.bic == str(self.banco_rfc).replace('_2',''):
                        net_total = sum(payslip.line_ids.filtered(lambda x:x.code=='EFECT').mapped('total'))
                        if net_total == 0:
                            continue
                        if self.employee_type == '02' and employee.diario_pago.bank_id.bic != employee.banco.bic:
                            continue
                        if self.employee_type == '03' and employee.diario_pago.bank_id.bic == employee.banco.bic:
                            continue
                        _logger.info('empleado %s --- banco %s', employee.name, self.banco_rfc)
                        if self.banco_rfc == 'BBA830831LJ2': # Bancomer Mixto
                           data1 = '3' # identificador
                           data2 = self.bbva_referencia[:7]
                           if not employee.rfc:
                               raise UserError(_('Falta RFC para el empleado %s.') % (employee.name))
                           data3 = employee.rfc and employee.rfc.ljust(18,' ')
                           if employee.tipo_cuenta == 'c_ahorro':
                               data4 = '40'
                               if len(employee.no_cuenta) != 18:
                                  raise UserError(_('En la cuenta del empleado debe colocar la CLABE interbancaria (18 digitos) para el empleado %s') % (employee.name))
                           elif employee.tipo_cuenta == 'cheques':
                               data4 = '01'
                               if len(employee.no_cuenta) != 10:
                                  raise UserError(_('En la cuenta del empleado debe colocar la cuenta BBVA Bancomer (10 digitos) para el empleado %s') % (employee.name))
                           else:
                               raise UserError(_('Los tipos de cuenta permitidos son "Cuenta de Ahorro" o "Cheques" para el empleado %s') % (employee.name))
                           if not employee.no_cuenta:
                               raise UserError(_('Falta número de cuenta para el empleado %s.') % (employee.name))
                           if employee.tipo_cuenta == 'c_ahorro':
                              data5 = employee.no_cuenta[:3] #posiciones 1, 2 y 3 de la cuenta CLABE
                              data6 = employee.no_cuenta[3:6] # posiciones 4, 5 y 6 de la cuenta CLABE.
                              data7 = employee.no_cuenta[6:].rjust(16,'0') #12 posiciones.
                           elif employee.tipo_cuenta == 'cheques':
                              data5 = '001' # posiciones 1, 2 y 3 de la cuenta CLABE
                              data6 = '001' # posiciones 4, 5 y 6 de la cuenta CLABE.
                              data7 = employee.no_cuenta.rjust(16,'0') #10 posiciones cuenta
                           data8 =  str(round(net_total,2)).split('.')[0].rjust(13, '0')
                           if net_total > 0:
                              data8b =  str(round(net_total,2)).split('.')[1].ljust(2, '0')
                           else:
                              data8b =  '00'
                           data9 = '0000000' # fillers
                           data10 = '                                                                                ' # fillers
                           nombre_empleado = employee.name.replace('/','').replace('-','').replace('.','').replace(':','').replace('?','').replace('&','').replace('!','')
                           nombre_empleado = nombre_empleado.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u')
                           nombre_empleado = nombre_empleado.replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U').replace('Ü','u')
                           nombre_empleado = nombre_empleado.replace('ñ','n').replace('Ñ','N')
                           data11 = nombre_empleado[0:40].ljust(40, ' ') # nombre del empleado
                           data12 = 'PAGO POR CONCEPTO DE NOMINA'.ljust(40, ' ')
                           file_text.append(data1 + data2 + data3 + data4 + data5 + data6 + data7 + data8 + data8b + data9 + data10 + data11 + data12 +'\r')
                        elif self.banco_rfc == 'BBA830831LJ2_2': # Dispersión de Bancomer solo cuentas BBVA
                           data1 = str(num_registro).zfill(9) # número consecutivo del registro
                           if not employee.rfc:
                               raise UserError(_('Falta RFC para el empleado %s.') % (employee.name))
                           data2 = employee.rfc and employee.rfc.ljust(16)[:16] or '                '  #rfc
                           if employee.tipo_cuenta == 'c_ahorro':
                               data3 = '40'
                               if len(employee.no_cuenta) != 18:
                                  raise UserError(_('En la cuenta del empleado debe colocar la CLABE interbancaria (18 digitos) para el empleado %s') % (employee.name))
                           elif employee.tipo_cuenta == 'cheques':
                               data3 = '99'
                               if len(employee.no_cuenta) != 10:
                                  raise UserError(_('En la cuenta del empleado debe colocar la cuenta BBVA Bancomer (10 digitos) para el empleado %s') % (employee.name))
                           else:
                               raise UserError(_('Los tipos de cuenta permitidos son "Cuenta de Ahorro" o "Cheques" para el empleado %s') % (employee.name))
                           if not employee.no_cuenta:
                               raise UserError(_('Falta número de cuenta para el empleado %s.') % (employee.name))
                           if employee.tipo_cuenta == 'c_ahorro':
                              data4 = employee.no_cuenta.ljust(20) #CLABE
                           elif employee.tipo_cuenta == 'cheques':
                              data4 = employee.no_cuenta.ljust(20) #NUMERO DE CUENTA 10 DIGITOS BANCOMER
                           data5 =  str(round(net_total,2)).split('.')[0].rjust(13, '0')
                           if net_total > 0:
                              data5b =  str(round(net_total,2)).split('.')[1].ljust(2, '0')
                           else:
                              data5b =  '00'
                           nombre_empleado = employee.name.replace('/','').replace('-','').replace('.','').replace(':','').replace('?','').replace('&','').replace('!','')
                           nombre_empleado = nombre_empleado.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u')
                           nombre_empleado = nombre_empleado.replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U').replace('Ü','u')
                           nombre_empleado = nombre_empleado.replace('ñ','n').replace('Ñ','N')
                           data6 = nombre_empleado[0:40].ljust(40, ' ') # nombre del empleado
                           if employee.tipo_cuenta == 'c_ahorro':
                              data7 = employee.no_cuenta[:3] #posiciones 1, 2 y 3 de la cuenta CLABE
                              data8 = employee.no_cuenta[3:6] # posiciones 4, 5 y 6 de la cuenta CLABE.
                           elif employee.tipo_cuenta == 'cheques':
                              data7 = '001' # posiciones 1, 2 y 3 de la cuenta CLABE
                              data8 = '001' # posiciones 4, 5 y 6 de la cuenta CLABE.
                           file_text.append((data1)+(data2)+(data3)+(data4)+(data5)+(data5b)+(data6)+(data7)+(data8)+'\r')
                           num_registro += 1
                        elif self.banco_rfc == 'BSM970519DU8': # Dispersión de Santander - solo cuentas santander
                           data1 = '2'
                           data2 = str(num_registro).zfill(5)
                           data3 = str(employee.no_empleado).ljust(7)
                           data4 = employee.empleado_paterno.ljust(30)[:30]
                           data5 = employee.empleado_materno.ljust(20)[:20]
                           data6 = employee.empleado_nombre.ljust(30)[:30]
                           if not employee.no_cuenta:
                               raise UserError(_('Falta número de cuenta para el empleado %s.') % (employee.name))
                           data7 = employee.no_cuenta.ljust(16)[:16]
                           data8 = str(round(net_total,2)).split('.')[0].rjust(16, '0')
                           if net_total > 0:
                              data8b =  str(round(net_total,2)).split('.')[1].ljust(2, '0')
                           else:
                              data8b =  '00'
                           #for var in data8b:
                           #   _logger.info('total %s', var)
                           data9 = self.dato1 or '' #'01'
                           file_text.append((data1)+(data2)+(data3)+(data4)+(data5)+(data6)+(data7)+(data8)+(data8b)+(data9))
                           num_registro += 1
                        elif self.banco_rfc == 'BSM970519DU8_2': # Dispersión de Santander - distintos bancos
                           data1 = '2'
                           data2 = str(num_registro).zfill(5)
                           data3 = employee.name[0:50].ljust(50, ' ')
                           if employee.tipo_cuenta == 't_debido':
                              data4 = '02'
                           elif employee.tipo_cuenta == 'cheques':
                              data4 = '01'
                           elif employee.tipo_cuenta == 'c_ahorro':
                              data4 = '40'
                           if not employee.no_cuenta:
                               raise UserError(_('Falta número de cuenta para el empleado %s.') % (employee.name))
                           data5 = employee.no_cuenta.ljust(20)
                           data6 = str(round(net_total,2)).replace('.','').rjust(18, '0')
                           data7 = employee.clave_santander_banco and employee.clave_santander_banco.rjust(5, '0') or '00000'
                           data8 = employee.plaza_santander_banco and employee.plaza_santander_banco.rjust(5, '0') or '00000'
                          # data9 = self.dato1
                           file_text.append((data1)+(data2)+(data3)+(data4)+(data5)+(data6)+(data7)+(data8))
                           num_registro += 1
                        elif self.banco_rfc == 'BNM840515VB1': # Banamex "C"
                           #3 0 001 01 001 000000000000242964 03 00005256781834028297 TRANSFER11      SALBADOR,SANTIAGO/     000000
                           data1 = '3'
                           data2 = '0'
                           data3 = '001'
                           data6 =  str(round(net_total,2)).split('.')[0].rjust(16, '0')
                           if net_total > 0:
                              data6a =  str(round(net_total,2)).split('.')[1].ljust(2, '0')
                           else:
                              data6a =  '00'
                           data7 = '01' # tipo de cuenta de abono 
                                        # 01: Cheques / CLABE
                                        # 03=Plásticos
                                        # 04=Orden de pago
                                        # 15=Cuenta concentradora
                           if not employee.no_cuenta:
                               raise UserError(_('Falta número de cuenta para el empleado %s.') % (employee.name))
                           data8 = employee.no_cuenta.rjust(20, '0')
                           if self.employee_type == '02':
                              data9 = (str(num_registro)).rjust(10, '0')
                              data9a = '                              '
                           else:
                              data9 = '000000000000000000000000000000'
                              data9a = (str(num_registro)).rjust(10, '0')
                           if not employee.empleado_nombre or not employee.empleado_paterno:
                               raise UserError(_('Falta nombre y/o apellido paterno para el empleado %s.') % (employee.name))
                           if employee.empleado_materno:
                              nombre_empleado = employee.empleado_nombre + ',' + employee.empleado_paterno + '/' + employee.empleado_materno
                           else:
                              nombre_empleado = employee.empleado_nombre + ',' + employee.empleado_paterno + '/'
                           nombre_empleado = nombre_empleado.replace('-','').replace('.','').replace(':','').replace('?','').replace('&','').replace('!','')
                           nombre_empleado = nombre_empleado.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
                           nombre_empleado = nombre_empleado.replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U')
                           nombre_empleado = nombre_empleado.replace('ñ','@').replace('Ñ','@')
                           data10 = nombre_empleado[0:55].ljust(55, ' ')
                           data11 = 'TRANSFERENCIA                           '
                           data12 = '                        '
                           data15 = '    ' if self.employee_type == '02' else '0' + employee.no_cuenta[0:3] # clave del banco, depende de opciones  # 0012
                           data16 = '       ' if self.employee_type == '02' else str(num_registro).rjust(7, '0') # Referencia bajo valor
                           data17 = '  '
                           file_text.append((data1)+(data2)+(data3)+(data6)+(data6a)+(data7)+(data8)+(data9)+(data9a)+(data10)+(data11)+(data12)+(data15)+(data16)+(data17))
                           num_registro += 1
                        elif self.banco_rfc == 'BNM840515VB1_2': # Banamex "D"
                           #3 0 001 01 001 000000000000242964 03 00005256781834028297 TRANSFER11      SALBADOR,SANTIAGO/     000000
                           data1 = '3'
                           data2 = '0'
                           data3 = '001' # metodo pago  001: Cuentas Banamex 
                                                       #002: Interbancario 
                                                       #003: Orden de Pago.
                           data4 = '01'  #tipo de pago 01 nominna -- hay varios
                           data5 = '001'
                           data6 =  str(round(net_total,2)).split('.')[0].rjust(16, '0')
                           if net_total > 0:
                              data6a =  str(round(net_total,2)).split('.')[1].ljust(2, '0')
                           else:
                              data6a =  '00'
                           data7 = '03' # tipo de cuenta de abono 
                                        #01: Cheques, sólo válido para Pago Banamex.
                                        #03: Plásticos, válido para Pago Interbancario y Banamex.
                                        #04: Orden de Pago.
                                        #40: CLABE.
                           data8 = '0000'
                           if not employee.no_cuenta:
                               raise UserError(_('Falta número de cuenta para el empleado %s.') % (employee.name))
                           data8a = employee.no_cuenta.ljust(16)
                           data9 = ('TRANSFER'+ str(num_registro)).ljust(16, ' ')
                           if not employee.empleado_nombre or not employee.empleado_paterno:
                               raise UserError(_('Falta nombre y/o apellido paterno para el empleado %s.') % (employee.name))
                           if employee.empleado_materno:
                              nombre_empleado = employee.empleado_nombre + ',' + employee.empleado_paterno + '/' + employee.empleado_materno
                           else:
                              nombre_empleado = employee.empleado_nombre + ',' + employee.empleado_paterno + '/'
                           nombre_empleado = nombre_empleado.replace('-','').replace('.','').replace(':','').replace('?','').replace('&','').replace('!','')
                           nombre_empleado = nombre_empleado.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
                           nombre_empleado = nombre_empleado.replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U')
                           nombre_empleado = nombre_empleado.replace('ñ','@').replace('Ñ','@')
                           data10 = nombre_empleado[0:55].ljust(55, ' ')
                           data11 = '                                   '
                           data12 = '                                   '
                           data13 = '                                   '
                           data14 = '                                   '
                           data15 = '0000' # clave del banco, depende de opciones
                           data16 = '00'
                           data17 = '                                                                            '
                           data18 = '                                                                            '
                           #data19 = '                                                                           '
                           #data20 = '                                                  '
                           file_text.append((data1)+(data2)+(data3)+(data4)+(data5)+(data6)+(data6a)+(data7)+(data8)+(data8a)+(data9)+(data10)+(data11)+(data12)+(data13)+(data14)+(data15)+(data16)+(data17)+(data18))
                           num_registro += 1
                        elif self.banco_rfc == 'BMN930209927': # Banorte
                           data1 = 'D'
                           data2 = self.fecha_dispersion.strftime('%Y%m%d')
                           if not employee.no_empleado:
                               raise UserError(_('Falta número de empleado %s.') % (employee.name))
                           data3 = str(employee.no_empleado).rjust(10,'0') #numero de empleado
                           data4 = '                                        ' #espacios en blanco
                           data5 = '                                        ' #espacios en blanco
                           data6 =  str(round(net_total,2)).split('.')[0].rjust(13, '0')
                           if net_total > 0:
                              data6a =  str(round(net_total,2)).split('.')[1].ljust(2, '0')
                           else:
                              data6a =  '00'
                           if not employee.banco.c_banco:
                               raise UserError(_('El banco seleccionado no tiene clave configurada %s.') % (employee.name))
                           data7 = employee.banco.c_banco # numero del banco receptor
                           if employee.tipo_cuenta == 't_debito' or employee.tipo_cuenta == 't_credito':
                               data8 = '03'
                           elif employee.tipo_cuenta == 'cheques':
                               data8 = '01'
                           else:
                               data8 = '40'
                           if not employee.no_cuenta:
                               raise UserError(_('Falta configurar número de cuenta %s.') % (employee.name))
                           data8a = employee.no_cuenta.rjust(18, '0')
                           data9 = '0'
                           data10 = ' '
                           data11 = '00000000'
                           data12 = '                  '
                           file_text.append((data1)+(data2)+(data3)+(data4)+(data5)+(data6)+(data6a)+(data7)+(data8)+(data8a)+(data9)+(data10)+(data11)+(data12))
                           num_registro += 1
                        elif self.banco_rfc == 'BRM940216EQ6': # Banregio
                           data1 = str(num_empleados + 1).rjust(5, '0') + ',' #secuencia
                           data2 = 'S' + ','
                           if not employee.no_cuenta:
                               raise UserError(_('Falta configurar número de cuenta %s.') % (employee.name))
                           data3 = employee.no_cuenta.rjust(20, '0') + ','
                           data4 =  str(round(net_total,2)).split('.')[0].rjust(13, '0') + ','
                           if net_total > 0:
                              data5 =  str(round(net_total,2)).split('.')[1].ljust(2, '0') + ','
                           else:
                              data5 =  '00' + ','
                           data6 = '0000000000000,00' + ',' #espacios en blanco
                           data7 = 'TRANSFERENCIA SPEI                      ' + ',' #espacios en blanco
                           data8 = '               '
                           file_text.append((data1)+(data2)+(data3)+(data4)+(data5)+(data6)+(data7)+(data8))
                           num_registro += 1
                        elif self.banco_rfc == 'HMI950125KG8': # HSBC

                           if not employee.no_cuenta:
                               raise UserError(_('Falta configurar número de cuenta %s.') % (employee.name))
                           data1 = employee.no_cuenta.rjust(10, '0') + ','
                           data2 =  str(round(net_total,2)).split('.')[0].rjust(12, '0')
                           if net_total > 0:
                              data3 =  str(round(net_total,2)).split('.')[1].ljust(2, '0') + ','
                           else:
                              data3 =  '00' + ','

                           data4 = 'ABONO POR PAGO DE NOMINA          ' + ','

                           if not employee.empleado_nombre or not employee.empleado_paterno:
                               raise UserError(_('Falta nombre y/o apellido paterno para el empleado %s.') % (employee.name))
                           if employee.empleado_materno:
                              nombre_empleado = employee.empleado_nombre + ' ' + employee.empleado_paterno + ' ' + employee.empleado_materno
                           else:
                              nombre_empleado = employee.empleado_nombre + ' ' + employee.empleado_paterno
                           nombre_empleado = nombre_empleado.replace('-','').replace('.','').replace(':','').replace('?','').replace('&','').replace('!','')
                           nombre_empleado = nombre_empleado.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
                           nombre_empleado = nombre_empleado.replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U')
                           nombre_empleado = nombre_empleado.replace('ñ','@').replace('Ñ','@')
                           data5 = nombre_empleado[0:35].ljust(35, ' ')

                           file_text.append((data1)+(data2)+(data3)+(data4)+(data5))
                           num_registro += 1
                        elif self.banco_rfc == 'SIN9412025I4': # Scotiabank
                           if not employee.no_cuenta:
                               raise UserError(_('Falta configurar número de cuenta %s.') % (employee.name))
                           data1 = 'EEDA'
                           data2 = '04' #01 - Efectivo en ventanilla,  02 - Cheque de caja en ventanilla, 03 - Cheque de caja central y 04 - Abono en cuenta.
                           data3 =  str(round(net_total,2)).split('.')[0].rjust(15, '0')
                           if net_total > 0:
                              data4 =  str(round(net_total,2)).split('.')[1].ljust(2, '0')
                           else:
                              data4 =  '00'

                           data5 = self.fecha_dispersion.strftime('%Y%m%d')
                           data6 = '01'
                           data7 = str(employee.no_empleado).ljust(2)

                           if not employee.empleado_nombre or not employee.empleado_paterno:
                               raise UserError(_('Falta nombre y/o apellido paterno para el empleado %s.') % (employee.name))
                           if employee.empleado_materno:
                              nombre_empleado = employee.empleado_nombre + ' ' + employee.empleado_paterno + ' ' + employee.empleado_materno
                           else:
                              nombre_empleado = employee.empleado_nombre + ' ' + employee.empleado_paterno
                           nombre_empleado = nombre_empleado.replace('-','').replace('.','').replace(':','').replace('?','').replace('&','').replace('!','')
                           nombre_empleado = nombre_empleado.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
                           nombre_empleado = nombre_empleado.replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U')
                           nombre_empleado = nombre_empleado.replace('ñ','@').replace('Ñ','@')
                           data8 = nombre_empleado[0:35].rjust(59, ' ')

                           data9 = '            '
                           data10 = self.scotia_referencia.rjust(16, '0')
                           data11 = employee.no_cuenta.rjust(30, '0')
                           data12 = '00000'
                           data13 = '                                        '
                           data14 = '1 '
                           data15 = '00000044044001' 
                           data16 = '01'
                           data17 = payslip.payslip_run_id.name.ljust(142, ' ')
                           data18 = '0000000000000000000000000'
                           data19 = '                      '

                           file_text.append((data1)+(data2)+(data3)+(data4)+(data5) + data6 + data7 + data8 + data9 + data10 + data11 + data12 + data13 + data14 + data15 + data16 + data17 + data18 + data19)
                        elif self.banco_rfc == 'BII931004P61': # Inbursa
                           if not employee.no_cuenta:
                               raise UserError(_('Falta configurar número de cuenta %s.') % (employee.name))
                           if self.employee_type == '01':
                               raise UserError(_('No se puede dispersar a todos los empledos, cambiar la opción en "Empleados a dispersar".'))
                           if self.employee_type == '02':
                              data1 = self.fecha_dispersion.strftime('%Y%m%d') + ','
                              data2 = self.inbursa_cuenta + ','
                              data3 = str(employee.no_cuenta) + ','
                              data4 = str(round(net_total,2)) + ','
                              data5 = payslip.number
                              file_text.append((data1)+(data2)+(data3)+(data4)+(data5))
                           if self.employee_type == '03':
                              data1 = self.fecha_dispersion.strftime('%Y%m%d') + ','
                              data2 = self.inbursa_cuenta + ','
                              data3 = employee.no_cuenta + ','
                              data4 = str(round(net_total,2)) + ',' + ','
                              data5 = payslip.number + ',' + ',' + ','
                              data6 = '2'
                              file_text.append((data1)+(data2)+(data3)+(data4)+(data5)+(data6))
                           num_registro += 1
                        elif self.banco_rfc == 'BBA9407071E1': # Banbajio
                           if not employee.no_cuenta:
                               raise UserError(_('Falta configurar número de cuenta %s.') % (employee.name))
                           data1 = '02'
                           data2 = (str(num_registro)).rjust(7, '0') 
                           data3 = '90'
                           data4 = self.fecha_dispersion.strftime('%Y%m%d')
                           data5 = '000030'
                           data6 =  str(round(net_total,2)).split('.')[0].rjust(13, '0')
                           if net_total > 0:
                              data7 =  str(round(net_total,2)).split('.')[1].ljust(2, '0')
                           else:
                              data7 =  '00'
                           data8 = self.fecha_dispersion.strftime('%Y%m%d')
                           data9 = '00'
                           data10 = self.diario_pago.bank_account_id.acc_number.rjust(20,'0') + ' '
                           data11 = employee.no_cuenta.rjust(22, '0') + ' '
                           data12 = (str(num_registro)).rjust(7, '0')
                           data13 = 'DEPOSITO DE NOMINA                      '
                           data14 = '0000000000000000000000000000000000000000'
                           file_text.append((data1)+(data2)+(data3)+(data4)+(data5)+(data6)+(data7)+(data8)+(data9)+(data10)+(data11)+(data12)+(data13)+(data14))
                           num_registro += 1

                        num_empleados += 1
                        monto_total += round(net_total,2)

              ##################################################################################
              ###################################################################################
              #sumario
              ###################################################################################
              ###################################################################################
            if self.banco_rfc == 'BBA830831LJ2': # Bancomer Mixto
                  enc1 = '1' 
                  enc2 = str(num_empleados).rjust(7, '0')
                  enc3 = str(round(monto_total,2)).split('.')[0].rjust(13, '0')
                  if monto_total > 0:
                      enc3a =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                      enc3a =  '00'
                  enc4 = '0000000'
                  enc5 = '000000000000000'
                  enc6 = '000000000000'
                  enc7 = self.bbva_no_contrato[:10]
                  enc8 = 'R05'
                  enc9 = '101'
                  enc10 = '1'
                  enc11 = datetime.now().strftime("%Y%m%d")
                  enc12 = self.fecha_dispersion.strftime('%Y%m%d')
                  enc13 = '                                                                                                                                              '
                  str_encabezado.append(enc1 + enc2 + enc3 + enc3a + enc4 + enc5 + enc6 + enc7 + enc8 + enc9+ enc10+ enc11+ enc12+ enc13 + '\r')
                  str_sumario.append('')
            elif self.banco_rfc == 'BBA830831LJ2_2': # Bancomer solo cuentas BBVA
                  str_sumario.append('')
            elif self.banco_rfc == 'BSM970519DU8' or self.banco_rfc == 'BSM970519DU8_2': # Santander
                   sum1 = '3'
                   sum2 = str(num_registro).rjust(5, '0')
                   sum3 = str(num_empleados).rjust(5, '0')
                   #sum4 = str(round(monto_total,2)).replace('.','').rjust(18, '0')
                   sum4 = str(round(monto_total,2)).split('.')[0].rjust(16, '0')
                   if monto_total > 0:
                      sum5 =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                   else:
                      sum5 =  '00'
                   str_sumario.append((sum1)+(sum2)+(sum3)+(sum4)+(sum5))
            elif self.banco_rfc == 'BNM840515VB1': # Banamex "C"
                  ### segundo encabezado  2 1 001 000000000037870848 01 00000000070020012747 000258
                  enc21 = '2' #FIJO
                  enc22 = '1' #FIJO
                  enc23 = '001' #Moneda nacional
                  enc24 = str(round(monto_total,2)).split('.')[0].rjust(16, '0')
                  if monto_total > 0:
                     enc24a =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                     enc24a =  '00'
                  enc25 = '01' #fijo cuenta de cheques
                  if self.diario_pago.bank_account_id.acc_number:
                     enc26 = self.diario_pago.bank_account_id.acc_number[0:4] + self.diario_pago.bank_account_id.acc_number[4:].rjust(20, '0')
                  else:
                     enc26 = '                  '
                  enc27 = '                    '
                  str_encabezado.append((enc21)+(enc22)+(enc23)+(enc24)+(enc24a)+(enc25)+(enc26)+(enc27))
                  #sumario
                  #4 001 000258 000000000037870848 000001 000000000037870848
                  sum1 = '4' #FIJO
                  sum2 = '001' #Moneda nacional
                  sum3 = str(num_empleados).rjust(6, '0')
                  sum4 = str(round(monto_total,2)).split('.')[0].rjust(16, '0')
                  if monto_total > 0:
                     sum4a =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                     sum4a =  '00'
                  sum5 = '000001'
                  sum6 = str(round(monto_total,2)).split('.')[0].rjust(16, '0')
                  if monto_total > 0:
                     sum6a =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                     sum6a =  '00'
                  str_sumario.append((sum1)+(sum2)+(sum3)+(sum4)+(sum4a)+(sum5)+(sum6)+(sum6a))
            elif self.banco_rfc == 'BNM840515VB1_2': # Banamex "D"
                  ### segundo encabezado  2 1 001 000000000037870848 01 00000000070020012747 000258
                  enc21 = '2' #FIJO
                  enc22 = '1' #FIJO
                  enc23 = '001' #Moneda nacional
                  enc24 = str(round(monto_total,2)).split('.')[0].rjust(16, '0')
                  if monto_total > 0:
                     enc24a =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                     enc24a =  '00'
                  enc25 = '01' #fijo cuenta de cheques
                  if self.diario_pago.bank_account_id.acc_number:
                     enc26 = self.diario_pago.bank_account_id.acc_number.rjust(20, '0')
                  else:
                     enc26 = '                  '
                  enc27 = str(num_empleados).rjust(6, '0')
                  str_encabezado.append((enc21)+(enc22)+(enc23)+(enc24)+(enc24a)+(enc25)+(enc26)+(enc27))
                  #sumario
                  #4 001 000258 000000000037870848 000001 000000000037870848
                  sum1 = '4' #FIJO
                  sum2 = '001' #Moneda nacional
                  sum3 = str(num_empleados).rjust(6, '0')
                  sum4 = str(round(monto_total,2)).split('.')[0].rjust(16, '0')
                  if monto_total > 0:
                     sum4a =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                     sum4a =  '00'
                  sum5 = '000001'
                  sum6 = str(round(monto_total,2)).split('.')[0].rjust(16, '0')
                  if monto_total > 0:
                     sum6a =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                     sum6a =  '00'
                  str_sumario.append((sum1)+(sum2)+(sum3)+(sum4)+(sum4a)+(sum5)+(sum6)+(sum6a))
            elif self.banco_rfc == 'BMN930209927': # Banorte
                  #primer encabezado
                  enc11 = 'H' #FIJO
                  enc12 = 'NE' #Nomina Banorte
                  enc13 = self.banorte_numero #numero de emisor asignado
                  enc14 = self.fecha_dispersion.strftime('%Y%m%d')
                  enc15 = '01' #no. consecutivo del 1-99
                  enc16 = str(num_empleados).rjust(6, '0') # numero de empleados
                  enc17 = str(round(monto_total,2)).split('.')[0].rjust(13, '0')
                  if monto_total > 0:
                     sum17a =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                     sum17a =  '00'
                  enc18 = '000000' # numero de altas
                  enc19 = '000000000000000' #impote total altas
                  enc20 = '000000' # numero de bajas
                  enc21 = '000000000000000' #impote total bajas
                  enc22 = '000000' # cuentas a veririfcar
                  enc23 = '0' #accion
                  enc24 = '00000000000000000000000000000000000000000000000000000000000000000000000000000' #filler 
                  str_encabezado.append(enc11+enc12+enc13+enc14+enc15+enc16+enc17+sum17a +enc18 + enc19+ enc20+ enc21+ enc22+ enc23+ enc24)
            elif self.banco_rfc == 'HMI950125KG8': # HSBC
                  #primer encabezado
                  enc11 = 'MXPRLF,' #FIJO
                  enc12 = 'F,' #fijo
                  if self.diario_pago.bank_account_id.acc_number:
                     enc13 = self.diario_pago.bank_account_id.acc_number.rjust(10, '0') + ','

                  enc14 = str(round(monto_total,2)).split('.')[0].rjust(12, '0')
                  if monto_total > 0:
                     enc15 =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')  + ','
                  else:
                     enc15 =  '00' + ','

                  enc16 = str(num_empleados).rjust(7, '0') + ','
                  enc17 = self.fecha_dispersion.strftime('%d%m%Y') + ','

                  enc18 = ',' # horario de programacion
                  enc19 = record.name

                  str_encabezado.append(enc11+enc12+enc13+enc14+enc15+enc16+enc17+enc18 + enc19)
            elif self.banco_rfc == 'SIN9412025I4': # Scotiabank
                  sum1 = 'EETB' #FIJO
                  sum2 = 'EETA' #Moneda nacional
                  sum3 = '0000006'
                  sum4 = str(round(monto_total,2)).split('.')[0].rjust(15, '0')
                  if monto_total > 0:
                     sum5a =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                     sum5a =  '00'
                  sum6 = '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
                  sum7 = '                                                                                                                           '

                  str_sumario.append((sum1)+(sum3)+(sum4)+(sum5a)+(sum6)+(sum7))
            elif self.banco_rfc == 'BII931004P61': # Inbursa
                  enc21 = str(num_empleados) + ','
                  enc22 = str(round(monto_total,2))
                  str_encabezado.append((enc21)+(enc22))
            elif self.banco_rfc == 'BBA9407071E1': # Banbajio
                  sum1 = '09' #FIJO
                  sum2 = str(num_registro).rjust(7, '0')
                  sum3 = '90' #FIJO
                  sum4 = str(num_empleados).rjust(7, '0')
                  sum5 = str(round(monto_total,2)).split('.')[0].rjust(16, '0')
                  if monto_total > 0:
                     sum6 =  str(round(monto_total,2)).split('.')[1].ljust(2, '0')
                  else:
                     sum6 =  '00'
                  sum7 = '                                                                                                                                                 '
                  str_sumario.append((sum1)+(sum2)+(sum3)+(sum4)+(sum5)+(sum6)+(sum7))
#            else:
#               raise Warning("Banco no compatible con la dispersión.")
        if not file_text:
            raise UserError(_('No hay información para generar el archivo de dispersión'))
        file_text = str_encabezado + file_text + str_sumario
        file_text = '\n'.join(file_text)
        file_text = file_text.encode()
        if self.banco_rfc == 'BMN930209927':
            filename = 'NI' + self.banorte_numero + '01.pag'
        elif self.banco_rfc == 'BII931004P61':
            filename = datetime.now().strftime("%y%m-%d%H%M%S")+'.csv'
        else:
            filename = datetime.now().strftime("%y%m-%d%H%M%S")+'.txt'
        self.write({'file_content':base64.b64encode(file_text)})
        return {
                'type' : 'ir.actions.act_url',
                'url': "/web/content/?model="+self._name+"&id=" + str(self.id) + "&field=file_content&download=true&filename="+filename+'&mimetype=text/plain',
                'target':'self',
                }
