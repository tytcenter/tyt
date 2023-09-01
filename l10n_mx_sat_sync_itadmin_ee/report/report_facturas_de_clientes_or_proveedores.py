# -*- coding: utf-8 -*-

import time
from odoo import api, models, tools
from lxml import etree
import base64
from lxml.objectify import fromstring

CFDI_XSLT_CADENA_TFD = 'l10n_mx_edi/data/xslt/3.3/cadenaoriginal_TFD_1_1.xslt'

class Reportfacturas_de_clientes(models.AbstractModel):
    _name ="report.l10n_mx_sat_sync_itadmin_ee.facturas_de_clientes"
    _description = 'Reportfacturas_de_clientes'

    @api.model
    def get_tax_amount_by_percent(self, lines):
        tax_amount_by_per = {}
        for line in lines:
            if not hasattr(line, 'Impuestos') or not hasattr(line.Impuestos, 'Traslados') or not hasattr(line.Impuestos.Traslados, 'Traslado'):
                continue
            for tax in line.Impuestos.Traslados.Traslado:
               tx = float(tax.get('TasaOCuota','0.0'))*100
               tx_per_str = str(tx)+'%'
               amount = float(tax.get('Importe','0.0'))
               if tx_per_str not in tax_amount_by_per:
                   tax_amount_by_per[tx_per_str] = amount
               else:
                   tax_amount_by_per[tx_per_str] += amount

            if not hasattr(line, 'Impuestos') or not hasattr(line.Impuestos, 'Retenciones') or not hasattr(line.Impuestos.Retenciones, 'Retencion'):
                continue
            for tax in line.Impuestos.Retenciones.Retencion:
               tx = float(tax.get('TasaOCuota','0.0'))*100
               tx_per_str = '-'+str(tx)+'%'
               amount = float(tax.get('Importe','0.0'))
               if tx_per_str not in tax_amount_by_per:
                   tax_amount_by_per[tx_per_str] = -amount
               else:
                   tax_amount_by_per[tx_per_str] += -amount
        return tax_amount_by_per
    
    @api.model
    def get_tax_amount(self,line):
        tax_per = []
        tax_amount = 0.0
            #return ['',0.0,{}]

        if hasattr(line, 'Impuestos') and hasattr(line.Impuestos, 'Traslados') and hasattr(line.Impuestos.Traslados, 'Traslado'):
            for tax in line.Impuestos.Traslados.Traslado:
               tx = float(tax.get('TasaOCuota','0.0'))*100
               tx_per_str = str(tx)+'%'
               tax_per.append(tx_per_str)
               amount = float(tax.get('Importe','0.0'))
               tax_amount += amount

        if hasattr(line, 'Impuestos') and hasattr(line.Impuestos, 'Retenciones') and  hasattr(line.Impuestos.Retenciones, 'Retencion'):
            for tax in line.Impuestos.Retenciones.Retencion:
               tx = float(tax.get('TasaOCuota','0.0'))*100
               tx_per_str = '-'+str(tx)+'%'
               tax_per.append(tx_per_str)
               amount = float(tax.get('Importe','0.0'))
               tax_amount += amount

        return [', '.join(tax_per), round(tax_amount,2)]

    @api.model
    def l10n_mx_edi_amount_to_text(self, currency, amount_total):
        for doc in self:
           currency_rec = doc.env['res.currency'].search([('name','=', currency)], limit=1)
           currency = currency.upper()
           # M.N. = Moneda Nacional (National Currency)
           # M.E. = Moneda Extranjera (Foreign Currency)
           currency_type = 'M.N' if currency == 'MXN' else 'M.E.'
           # Split integer and decimal part
           amount_i, amount_d = divmod(amount_total, 1)
           amount_d = round(amount_d, 2)
           amount_d = int(round(amount_d * 100, 2))
           words = currency_rec.with_context(lang=doc.env.user.lang or 'es_ES').amount_to_text(amount_i).upper()
           invoice_words = '%(words)s %(amount_d)02d/100 %(curr_t)s' % dict(
               words=words, amount_d=amount_d, curr_t=currency_type)
           return invoice_words

    @api.model
    def l10n_mx_edi_get_xml_etree(self, cfdi=None):
        return fromstring(base64.decodebytes(cfdi)) if cfdi else None

    @api.model
    def l10n_mx_edi_get_tfd_etree(self, cfdi):
        if not hasattr(cfdi, 'Complemento'):
            return None
        attribute = 'tfd:TimbreFiscalDigital[1]'
        namespace = {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'}
        node = cfdi.Complemento.xpath(attribute, namespaces=namespace)
        return node[0] if node else None

    @api.model
    def l10n_mx_edi_generate_cadena(self, xslt_path, cfdi_as_tree):
        xslt_root = etree.parse(tools.file_open(xslt_path))
        return str(etree.XSLT(xslt_root)(cfdi_as_tree))

    @api.model
    def _get_l10n_mx_edi_cadena(self, cfdi):
        
        #get the xslt path
        xslt_path = CFDI_XSLT_CADENA_TFD
        #get the cfdi as eTree
        #cfdi = base64.decodebytes(self.l10n_mx_edi_cfdi)
        cfdi = self.l10n_mx_edi_get_xml_etree(cfdi)
        cfdi = self.l10n_mx_edi_get_tfd_etree(cfdi)
        #return the cadena
        return self.l10n_mx_edi_generate_cadena(xslt_path, cfdi)

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'ir.attachment',
            'data': data,
            'docs': self.env['ir.attachment'].browse(docids),
            'time': time,
            #'base64': base64,
            'round': round,
            'get_tax_amount': self.get_tax_amount,
            'l10n_mx_edi_amount_to_text': self.l10n_mx_edi_amount_to_text,
            'l10n_mx_edi_get_xml_etree': self.l10n_mx_edi_get_xml_etree,
            'l10n_mx_edi_get_tfd_etree': self.l10n_mx_edi_get_tfd_etree,
            '_get_l10n_mx_edi_cadena': self._get_l10n_mx_edi_cadena,
            'get_tax_amount_by_percent' : self.get_tax_amount_by_percent,
            }
