# -*- coding: utf-8 -*-
from odoo import models,fields, api, _
from odoo.exceptions import UserError
import base64

class XMLInvoiceReconcile(models.TransientModel):
    _name ='xml.invoice.reconcile'
    _description = 'XMLInvoiceReconcile'

    attachment_id = fields.Many2one('ir.attachment',"Xml Attachment")
    invoice_id = fields.Many2one('account.move',"Invoice")
    payment_id = fields.Many2one('account.payment',"Payment")
    date = fields.Date("Date")
    #partner_id = fields.Many2one("res.partner","Client")
    client_name = fields.Char("Client")
    amount = fields.Float("Amount")
    reconcilled = fields.Boolean("Is Reconcilled ?")
    moneda = fields.Char("Moneda")

    folio_fiscal = fields.Char("Folio Fiscal")
    folio_factura = fields.Char("Folio factura")
    forma_pago = fields.Selection(
        selection=[('01', '01 - Efectivo'), 
                   ('02', '02 - Cheque nominativo'), 
                   ('03', '03 - Transferencia electrónica de fondos'),
                   ('04', '04 - Tarjeta de Crédito'), 
                   ('05', '05 - Monedero electrónico'),
                   ('06', '06 - Dinero electrónico'), 
                   ('08', '08 - Vales de despensa'), 
                   ('12', '12 - Dación en pago'), 
                   ('13', '13 - Pago por subrogación'), 
                   ('14', '14 - Pago por consignación'), 
                   ('15', '15 - Condonación'), 
                   ('17', '17 - Compensación'), 
                   ('23', '23 - Novación'), 
                   ('24', '24 - Confusión'), 
                   ('25', '25 - Remisión de deuda'), 
                   ('26', '26 - Prescripción o caducidad'), 
                   ('27', '27 - A satisfacción del acreedor'), 
                   ('28', '28 - Tarjeta de débito'), 
                   ('29', '29 - Tarjeta de servicios'), 
                   ('30', '30 - Aplicación de anticipos'), 
                   ('31', '31 - Intermediario pagos'), 
                   ('99', '99 - Por definir'),],
        string=_('Forma de pago'),
    )
    uso_cfdi = fields.Selection(
        selection=[('G01', _('Adquisición de mercancías')),
                   ('G02', _('Devoluciones, descuentos o bonificaciones')),
                   ('G03', _('Gastos en general')),
                   ('I01', _('Construcciones')),
                   ('I02', _('Mobiliario y equipo de oficina por inversiones')),
                   ('I03', _('Equipo de transporte')),
                   ('I04', _('Equipo de cómputo y accesorios')),
                   ('I05', _('Dados, troqueles, moldes, matrices y herramental')),
                   ('I06', _('Comunicacion telefónica')),
                   ('I07', _('Comunicación Satelital')),
                   ('I08', _('Otra maquinaria y equipo')),
                   ('D01', _('Honorarios médicos, dentales y gastos hospitalarios')),
                   ('D02', _('Gastos médicos por incapacidad o discapacidad')),
                   ('D03', _('Gastos funerales')),
                   ('D04', _('Donativos')),
                   ('D07', _('Primas por seguros de gastos médicos')),
                   ('D08', _('Gastos de transportación escolar obligatoria')),
                   ('D10', _('Pagos por servicios educativos (colegiaturas)')),
                   ('S01', _('Sin efectos fiscales')),
                   ('CP01', _('Pago')),
                   ('CN01', _('Nomina')),
                   ('P01', _('Por definir')),],
        string=_('Uso CFDI (cliente)'),
    )
    
    numero_cetificado = fields.Char("Numero cetificado")
    fecha_certificacion = fields.Char("Fecha certificacion")
    selo_digital_cdfi = fields.Char("Sello digital CFDI")
    selo_sat = fields.Char("Sello SAT")
    tipocambio = fields.Char("Tipo cambio")
    tipo_comprobante = fields.Selection(
        selection=[('I', 'Ingreso'), 
                   ('E', 'Egreso'),
                   ('P', 'Pago'),
                   ('N', 'Nomina'),
                    ('T', 'Traslado'),],
        string=_('Tipo de comprobante'),
    )
    fecha_factura = fields.Datetime(string=_('Fecha Factura'))
    number_folio = fields.Char(string=_('Folio'))
    invoice_type = fields.Char("Invoice Type")
    payment_type = fields.Char("Payment Type")
    client_rfc = fields.Char("RFC")

    def action_reconcile(self):
        self.ensure_one()
        invoice = self.invoice_id
        payment = self.payment_id
        if not invoice and not payment:
            raise UserError("Seleccionar primero la factura/pago y posteriormente reconciliar con el XML.")

        if invoice:
            if self.env['ir.config_parameter'].sudo().get_param('l10n_mx_sat_sync_itadmin_ee.tipo_conciliacion') == '01':
               if invoice.amount_total != self.amount:
                   raise UserError("El total de la factura y el XML son distintos")
            else:
               diff = self.env['ir.config_parameter'].sudo().get_param('l10n_mx_sat_sync_itadmin_ee.rango')
               if (invoice.amount_total < (self.amount - float(diff))) or  (invoice.amount_total > (self.amount + float(diff))):
                   raise UserError("El total de la factura no está dentro del rango permitido")
            invoice.write({'l10n_mx_edi_cfdi_uuid': self.folio_fiscal,
                           'l10n_mx_edi_usage' : self.uso_cfdi if self.uso_cfdi != 'S01' else 'P01',
                           #'l10n_mx_edi_cfdi_name' : self.attachment_id.store_fname,
                           #'l10n_mx_edi_cfdi_certificate_id' : self.numero_cetificado,
                           })
            self.attachment_id.write({'creado_en_odoo':True, 'invoice_ids':[(6,0, [invoice.id])], 'res_id': invoice.id, 'res_model': invoice._name,})
#            _logger.info("Factura conciliada")
            invoice._compute_cfdi_uuid()
            self.write({'reconcilled':True})
        if payment:
            if self.env['ir.config_parameter'].sudo().get_param('l10n_mx_sat_sync_itadmin_ee.tipo_conciliacion') == '01':
               if payment.amount_total != self.amount:
                   raise UserError("El total de la factura y el XML son distintos")
            else:
               diff = self.env['ir.config_parameter'].sudo().get_param('l10n_mx_sat_sync_itadmin_ee.rango')
               if  payment.amount_total < self.amount - float(diff) or payment.amount_total > self.amount + float(diff):
                   raise UserError("El total de la factura no está dentro del rango permitido")
            payment.write({'l10n_mx_edi_cfdi_uuid': self.folio_fiscal,
                           #'l10n_mx_edi_cfdi_name' : self.attachment_id.store_fname,
                           })
            self.attachment_id.write({'creado_en_odoo':True, 'payment_ids':[(6,0, [payment.id])], 'res_id': payment.id, 'res_model': payment._name,})
#            _logger.info("Factura reconciliada")
            self.write({'reconcilled':True})
        return
