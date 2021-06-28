# -*- coding: utf-8 -*-
from odoo import models,fields,api

class ImportInvoiceProcessMessage(models.TransientModel):
    _name ='import.invoice.process.message'
    _description = 'ImportInvoiceProcessMessage'
    
    name = fields.Char("Name")
    
    
    def show_created_invoices(self):
        create_invoice_ids = self._context.get('create_invoice_ids',[])
        action = self.env.ref('account.action_move_in_invoice_type')
        result = action.read()[0]
        result['context'] = {'type': 'in_invoice'}
        result['domain'] = "[('id', 'in', " + str(create_invoice_ids) + ")]"
        return result
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ImportInvoiceProcessMessage, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type=='form':
            context = self._context
            if context.get('existed_attachment'):
                res['arch'] = res['arch'].replace("existed_attachment_content",context.get('existed_attachment'))
            else:
                res['arch'] = res['arch'].replace("existed_attachment_content",'')
            if context.get('not_imported_attachment'):
                res['arch'] = res['arch'].replace("not_imported_attachment_content",context.get('not_imported_attachment'))
            else:
                res['arch'] = res['arch'].replace("not_imported_attachment_content",'')
            if context.get('imported_attachment'):
                res['arch'] = res['arch'].replace("imported_attachment_content",context.get('imported_attachment'))
            else:
                res['arch'] = res['arch'].replace("imported_attachment_content",'')
                
            
        return res