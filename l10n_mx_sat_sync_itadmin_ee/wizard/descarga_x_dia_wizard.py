# -*- coding: utf-8 -*-
from odoo import models,fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime

class DescargaXDiaWizard(models.TransientModel):
    _name ='descarga.x.dia.wizard'
    _description = 'DescargaXDiaWizard'

    start_date = fields.Date("Fecha de inicio")
    end_date = fields.Date("Fecha Final")

    def download_cfdi_invoices_btw_two_dates(self):
        start_date = self.start_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
        start_date += ' 00:00:00'
        start_date = datetime.strptime(start_date,DEFAULT_SERVER_DATETIME_FORMAT)

        end_date = self.end_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
        end_date += ' 23:59:59'
        end_date = datetime.strptime(end_date,DEFAULT_SERVER_DATETIME_FORMAT)
        if self.env['ir.config_parameter'].sudo().get_param('l10n_mx_sat_sync_itadmin_ee.download_type') == 'API':
            self.env.company.sudo().download_cfdi_invoices_api(start_date, end_date)
        else:
            self.env.company.sudo().download_cfdi_invoices_web(start_date, end_date)
        return True
