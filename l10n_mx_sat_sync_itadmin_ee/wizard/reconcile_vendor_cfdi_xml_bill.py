# -*- coding: utf-8 -*-
from odoo import models,fields,api
import base64
#from lxml import etree
import json, xmltodict
#from .cfdi_invoice import convert_to_special_dict
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.parser import parse
from odoo.exceptions import UserError

#from .special_dict import CaselessDictionary
from ...l10n_mx_sat_sync_itadmin_ee.models.special_dict import CaselessDictionary

import logging
_logger = logging.getLogger(__name__)

def convert_to_special_dict(d):
    for k, v in d.items():
        if isinstance(v, dict):
            d.__setitem__(k, convert_to_special_dict(CaselessDictionary(v)))
        else:
            d.__setitem__(k, v)
    return d

class ReconcileVendorCfdiXmlBill(models.TransientModel):
    _name ='reconcile.vendor.cfdi.xml.bill'
    _description = 'ReconcileVendorCfdiXmlBill'
    
    typo_de_combante = fields.Selection([('I','Facturas de clientes'),
                                         ('SI', 'Facturas de proveedor'), 
                                         ('P', 'Pagos de clientes'),
                                         ('SP', 'Pagos de proveedor'),
                                         ('E', 'Notas de crédito clientes'),
                                         ('SE', 'Notas de crédito proveedor'),
                                         ], string='Tipo de Comprobante')

    def action_reconcile(self):
        #selected_att_ids = self._context.get('select_ids',[])
        selected_att_ids = self._context.get('active_ids')

        if not selected_att_ids or self._context.get('active_model','')!='ir.attachment':
            return

        attachments = self.env['ir.attachment'].sudo().search([('id','in', selected_att_ids), ('creado_en_odoo','!=',True), ('cfdi_type','=', self.typo_de_combante)])

        invoice_obj = self.env['account.move'].sudo()
        payment_obj = self.env['account.payment'].sudo()
        reconcile_obj = self.env['xml.invoice.reconcile'].sudo()

        created_ids = []
        invoice_type, payment_type = '', ''
        if self.typo_de_combante in ['I','P']:
            element_tag = 'Receptor'
            invoice_type = 'out_invoice'
            payment_type = 'inbound'
        elif self.typo_de_combante in ['SI','SP']:
            element_tag = 'Emisor'
            invoice_type = 'in_invoice'
            payment_type = 'outbound'
        elif self.typo_de_combante in ['E']:
            element_tag = 'Receptor'
            invoice_type = 'out_refund'
            payment_type = 'outbound'
        elif self.typo_de_combante in ['SE']:
            element_tag = 'Emisor'
            invoice_type = 'in_refund'
            payment_type = 'inbound'
        for attachment in attachments:
            file_content = base64.b64decode(attachment.datas)
            if b'xmlns:schemaLocation' in file_content:
                file_content = file_content.replace(b'xmlns:schemaLocation', b'xsi:schemaLocation')
            file_content = file_content.replace(b'cfdi:',b'')
            file_content = file_content.replace(b'tfd:',b'')
            try:
                data = json.dumps(xmltodict.parse(file_content)) #,force_list=('Concepto','Traslado',)
                data = json.loads(data)
            except Exception as e:
                data = {}
                raise UserError(str(e))

            data = CaselessDictionary(data)
            data = convert_to_special_dict(data)
            
            invoice_date = data.get('Comprobante',{}).get('@Fecha')
            Complemento = data.get('Comprobante',{}).get('Complemento',{})
            version = data.get('Comprobante',{}).get('@Version')

            if self.typo_de_combante in ['P','SP']:
               total = 0
               if version == '4.0':
                  total = eval(Complemento.get('pago20:Pagos').get('pago20:Totales').get('@MontoTotalPagos','0.0'))
               else:
                  try:
                    total = eval(Complemento.get('pago10:Pagos').get('pago10:Pago').get('@Monto','0.0'))
                  except Exception as e:
                     for payment in Complemento.get('pago10:Pagos').get('pago10:Pago'):
                         total += float(payment.get('@Monto','0.0'))
            else:
               total = eval(data.get('Comprobante',{}).get('@Total','0.0'))

            cust_data = data.get('Comprobante',{}).get(element_tag,{})
            uso_data = data.get('Comprobante',{}).get('Receptor',{})
            client_rfc = cust_data.get('@rfc')
            client_name = cust_data.get('@nombre')
            
            timbrado_data = Complemento.get('TimbreFiscalDigital',{})

            vals = {
                'invoice_type': invoice_type,
                'payment_type': payment_type,
                'client_name' : client_name,
                'client_rfc' : client_rfc,
                'date' : invoice_date, #tree_attrib_dict.get('fecha'),
                'amount' : total,
                'attachment_id' : attachment.id,
                'tipo_comprobante': data.get('Comprobante',{}).get('@TipoDeComprobante',{}),
                'folio_fiscal':timbrado_data.get('@UUID'),
                'forma_pago': data.get('Comprobante',{}).get('@FormaPago',''),
#                 'methodo_pago': data.get('Comprobante',{}).get('@MetodoPago',''),
                'numero_cetificado': timbrado_data.get('@NoCertificadoSAT'),
                'fecha_certificacion': timbrado_data.get('@FechaTimbrado'),
                'selo_digital_cdfi': timbrado_data.get('@SelloCFD'),
                'selo_sat': timbrado_data.get('@SelloSAT'),
                'tipocambio': data.get('Comprobante',{}).get('@TipoCambio'),
                'moneda': data.get('Comprobante',{}).get('@Moneda'),
                'folio_factura': data.get('Comprobante',{}).get('@Folio'),
                'fecha_factura': timbrado_data.get('@FechaTimbrado') and parse(timbrado_data.get('@FechaTimbrado')).strftime(DEFAULT_SERVER_DATETIME_FORMAT) or False,
                'uso_cfdi': uso_data.get('@UsoCFDI'),
                }
            if self.typo_de_combante in ['P','SP']:
                payments = payment_obj.search([('partner_id.vat','=',client_rfc),('amount','=',total),('payment_type','=', payment_type)])
                if payments:
                    payment = payments.filtered(lambda x:x.state in ['draft','sent'])
                    if payment:
                        vals.update({'payment_id':payment[0].id})
                    else:
                        vals.update({'payment_id':payments[0].id})
            else:
                invoices = invoice_obj.search([('partner_id.vat','=',client_rfc),('amount_total','=',total),('move_type','=', invoice_type)])
                if invoices:
                    inv = invoices.filtered(lambda x:x.state in ['open','draft'])
                    if inv:
                        vals.update({'invoice_id':inv[0].id})
                    else:
                        vals.update({'invoice_id':invoices[0].id})

            record = reconcile_obj.create(vals)
            created_ids.append(record.id)
        if self.typo_de_combante in ['P','SP']:
            action_id = 'l10n_mx_sat_sync_itadmin_ee.action_xml_payment_reconcile_view'
        else:
            action_id = 'l10n_mx_sat_sync_itadmin_ee.action_xml_invoice_reconcile_view'

        #action = self.env.ref(action_id).sudo().read()[0]
        action = self.env['ir.actions.act_window']._for_xml_id(action_id)
        action['domain'] = [('id', 'in', created_ids)]
        return action
