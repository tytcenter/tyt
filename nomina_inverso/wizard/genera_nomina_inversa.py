# -*- coding: utf-8 -*-
from odoo import models, fields,api,_
import io, os
import base64
import xlrd
from odoo.exceptions import Warning


class GeneraNominaInversa(models.TransientModel):
    _name = "genera.nomina.inversa"

    import_file = fields.Binary("Import Product",required=False)
    file_name = fields.Char("File")

    def generar_nomina_inversa(self):
        self.ensure_one()
        if not self.import_file:
            raise Warning("Please select the file first.") 
        p, ext = os.path.splitext(self.file_name)
        if ext[1:] not in ['xls', 'xlsx']:    
            raise Warning(_("Unsupported file format \"{}\", import only supports  xls, xlsx").format(self.file_name))
        wb = xlrd.open_workbook(file_contents=base64.decodestring(self.import_file))
        header=False
        for sheet in wb.sheets():
            for row in range(sheet.nrows):
                if header == False:
                    header = True
                    continue
                xls_data=[]
                for col in range(sheet.ncols):
                    xls_data.append(sheet.cell(row,col).value)
                    employee_id =self.env['hr.employee'].search([('no_empleado','=',int(xls_data[0]))])
                if employee_id:
                    monto =xls_data[1]
                    employee_id.contract_id.compute_sueldo_neto(monto)
                    vals={'employee_ids':[(6,0,[employee_id.id])]}
                    employee_payslip=self.env['hr.payslip.employees'].create(vals)
                    employee_payslip.compute_sheet()
