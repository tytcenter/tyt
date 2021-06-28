# -*- coding: utf-8 -*-

from odoo import models, fields, api
import base64

DEFAULT_CFDI_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

class AccountPayment(models.Model):
    _inherit = 'account.payment'
        
    attachment_id = fields.Many2one("ir.attachment", 'Attachment')
    l10n_mx_edi_cfdi_uuid_cusom = fields.Char(string='Fiscal Folio UUID', copy=False, readonly=True, compute="_compute_cfdi_uuid", store=True)
    
   
    @api.depends('l10n_mx_edi_cfdi_name')
    def _compute_cfdi_uuid(self):
        for payment in self:
            attachment_id = payment.l10n_mx_edi_retrieve_last_attachment()
            if not attachment_id:
                payment.l10n_mx_edi_cfdi_uuid_cusom=False
            else:
               #attachment = attachment[0]
                datas = attachment_id._file_read(attachment_id.store_fname)
                
                tree = payment.l10n_mx_edi_get_xml_etree(base64.decodestring(datas))
                # if already signed, extract uuid
                tfd_node = payment.l10n_mx_edi_get_tfd_etree(tree)
                if tfd_node is not None:
                    payment.l10n_mx_edi_cfdi_uuid_cusom = tfd_node.get('UUID')
