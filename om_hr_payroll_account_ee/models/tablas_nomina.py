# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class TablasCFDI(models.Model):
    _inherit= 'tablas.cfdi'

    pat_cuota_fija_pat_deb = fields.Many2one('account.account', string='Debito Cuota fija patronal', domain=[('deprecated', '=', False)])
    pat_exedente_smg_deb = fields.Many2one('account.account', string='Debito Exedente 3 SMGDF.', domain=[('deprecated', '=', False)])
    pat_prest_dinero_deb = fields.Many2one('account.account', string='Debito Prest en dinero.', domain=[('deprecated', '=', False)])
    pat_esp_pens_deb = fields.Many2one('account.account', string='Debito Gastos médicos.', domain=[('deprecated', '=', False)])
    pat_riesgo_trabajo_deb = fields.Many2one('account.account', string='Debito Riegso de trabajo', domain=[('deprecated', '=', False)])
    pat_invalidez_vida_deb = fields.Many2one('account.account', string='Debito Invalidez y Vida', domain=[('deprecated', '=', False)])
    pat_guarderias_deb = fields.Many2one('account.account', string='Debito Guarderias y PS', domain=[('deprecated', '=', False)])
    pat_retiro_deb = fields.Many2one('account.account', string='Debito Retiro', domain=[('deprecated', '=', False)])
    pat_cesantia_vejez_deb = fields.Many2one('account.account', string='Debito Cesantia y vejez.', domain=[('deprecated', '=', False)])
    pat_infonavit_deb = fields.Many2one('account.account', string='Debito INFONAVIT', domain=[('deprecated', '=', False)])
    pat_total_deb = fields.Many2one('account.account', string='Debito IMSS patron', domain=[('deprecated', '=', False)])

    pat_cuota_fija_pat_cre = fields.Many2one('account.account', string='Credito Cuota fija patronal', domain=[('deprecated', '=', False)])
    pat_exedente_smg_cre = fields.Many2one('account.account', string='Credito Exedente 3 SMGDF.', domain=[('deprecated', '=', False)])
    pat_prest_dinero_cre = fields.Many2one('account.account', string='Credito Prest en dinero.', domain=[('deprecated', '=', False)])
    pat_esp_pens_cre = fields.Many2one('account.account', string='Credito Gastos médicos.', domain=[('deprecated', '=', False)])
    pat_riesgo_trabajo_cre = fields.Many2one('account.account', string='Credito Riegso de trabajo', domain=[('deprecated', '=', False)])
    pat_invalidez_vida_cre = fields.Many2one('account.account', string='Credito Invalidez y Vida', domain=[('deprecated', '=', False)])
    pat_guarderias_cre = fields.Many2one('account.account', string='Credito Guarderias y PS', domain=[('deprecated', '=', False)])
    pat_retiro_cre = fields.Many2one('account.account', string='Credito Retiro', domain=[('deprecated', '=', False)])
    pat_cesantia_vejez_cre = fields.Many2one('account.account', string='Credito Cesantia y vejez.', domain=[('deprecated', '=', False)])
    pat_infonavit_cre = fields.Many2one('account.account', string='Credito INFONAVIT', domain=[('deprecated', '=', False)])
    pat_total_cre = fields.Many2one('account.account', string='Credito IMSS patron', domain=[('deprecated', '=', False)])