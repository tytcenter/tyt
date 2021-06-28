# -*- coding: utf-8 -*-

from odoo import models, fields, api
import base64
from lxml import etree

import logging
_logger = logging.getLogger(__name__)

from .special_dict import CaselessDictionary

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    
    @api.depends('invoice_ids')
    def _compute_account_invoice_count(self):
        for attach in self:
            try:
                attach.invoice_count = len(attach.invoice_ids)
            except Exception:
                pass
            
    @api.depends('payment_ids')
    def _compute_account_payment_count(self):
        for attach in self:
            try:
                attach.payment_count = len(attach.payment_ids)
            except Exception:
                pass
                
    cfdi_uuid = fields.Char("CFDI UUID", copy=False)
    #cfdi_type = fields.Selection([('E','Emisor'),('R','Receptor')],"CFDI Invoice Type", copy=False)
    cfdi_type = fields.Selection([
    ('I', 'Facturas de clientes'), #customer invoice, Emisor.RFC=myself.VAT, Customer invoice
    ('SI', 'Facturas de proveedor'), #Emisor.RFC!=myself.VAT, Supplier bill
    ('E', 'Notas de crédito clientes'), #customer credit note, Emisor.RFC=myself.VAT, Customer credit note
    ('SE', 'Notas de crédito proveedor'), #Emisor.RFC!=myself.VAT, Supplier credit note
    ('P', 'REP de clientes'), #Emisor.RFC=myself.VAT, Customer payment receipt
    ('SP', 'REP de proveedores'), #Emisor.RFC!=myself.VAT, Supplier payment receipt
    ('N', 'Nominas de empleados'), #currently we shall not do anythong with this type of cfdi, Customer Payslip
    ('SN', 'Nómina propia'), #currently we shall not do anythong with this type of cfdi, Supplier Payslip
    ('T', 'Factura de traslado cliente'), #currently we shall not do anythong with this type of cfdi, WayBill Customer
    ('ST', 'Factura de traslado proveedor'),], #currently we shall not do anythong with this type of cfdi, WayBill Supplier                
    "Tipo de comprobante", 
    copy=False)

    date_cfdi = fields.Date('Fecha')
    rfc_tercero = fields.Char("RFC tercero")
    nombre_tercero = fields.Char("Nombre tercero")
    cfdi_total = fields.Float("Importe")
    creado_en_odoo = fields.Boolean("Creado en odoo", copy=False)
    invoice_ids = fields.One2many("account.move",'attachment_id',"Facturas")
    invoice_count = fields.Integer(compute='_compute_account_invoice_count', string='# de facturas', store=True)
    
    payment_ids = fields.One2many("account.payment",'attachment_id',"Pagos")
    payment_count = fields.Integer(compute='_compute_account_payment_count', string='# de pagos', store=True)
    
    serie_folio = fields.Char("Folio")

    @api.model
    def create(self, vals):
        ctx = self._context.copy()
        if ctx.get('is_fiel_attachment'):
            datas = vals.get('datas')
            if datas:
                xml_content = base64.b64decode(datas)
                if b'xmlns:schemaLocation' in xml_content:
                    xml_content = xml_content.replace(b'xmlns:schemaLocation', b'xsi:schemaLocation')
                try:
                    tree = etree.fromstring(xml_content)
                except Exception as e:
                    _logger.error('error : '+str(e))
                    raise
                try:
                    ns = tree.nsmap
                    ns.update({'re': 'http://exslt.org/regular-expressions'})
                except Exception:
                    ns = {'re': 'http://exslt.org/regular-expressions'}
                    
                tfd_namespace = {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'}
                tfd_elements = tree.xpath("//tfd:TimbreFiscalDigital", namespaces=tfd_namespace)
                tfd_uuid = tfd_elements and tfd_elements[0].get('UUID')
                cfdi_type = vals.get('cfdi_type','I')
                
                if cfdi_type in ['I','E','P','N','T']:
                    element_tag = 'Receptor'
                else:
                    element_tag = 'Emisor'
                try:
                    elements = tree.xpath("//*[re:test(local-name(), '%s','i')]"%(element_tag), namespaces=ns)
                except Exception:
                    _logger.info("No encontró al Emisor/Receptor")
                    elements = None
                client_rfc, client_name = '', ''
                if elements:
                    attrib_dict = CaselessDictionary(dict(elements[0].attrib))
                    client_rfc = attrib_dict.get('rfc') 
                    client_name = attrib_dict.get('nombre')
                    
                vals.update({
                        'cfdi_uuid' :tfd_uuid,
                        'rfc_tercero' : client_rfc,
                        'nombre_tercero' : client_name,
                        'cfdi_total' : tree.get('Total', tree.get('total')),
                        'date_cfdi' : tree.get('Fecha',tree.get('fecha')),
                        'serie_folio' : tree.get('Folio',tree.get('folio'))
                    })
        return super(IrAttachment, self).create(vals)
    
    def action_view_payments(self):
        payments = self.mapped('payment_ids')
        if payments and payments[0].payment_type=='outbound':
            action = self.env.ref('account.action_account_payments_payable').read()[0]
        else:
            action = self.env.ref('account.action_account_payments').read()[0]
        
        if len(payments) > 1:
            action['domain'] = [('id', 'in', payments.ids)]
        elif len(payments) == 1:
            action['views'] = [(self.env.ref('account.view_account_payment_form').id, 'form')]
            action['res_id'] = payments.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
            
    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
            action['view_mode'] = 'tree'
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    
    def action_renmove_invoice_link(self):
        for attach in self:
            if attach.invoice_ids:
                attach.invoice_ids.write({'attachment_id' : False})
            if attach.payment_ids:
                attach.payment_ids.write({'attachment_id' : False})
            vals = {'res_id':False, 'res_model':False} #'l10n_mx_edi_cfdi_name':False
            if attach.creado_en_odoo:
                vals.update({'creado_en_odoo':False})
                #attach.creado_en_odoo=False
            attach.write(vals)
        return True