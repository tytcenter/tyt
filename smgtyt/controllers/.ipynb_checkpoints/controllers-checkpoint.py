#-*- coding: utf-8 -*-
from odoo import http


class Smgtyt(http.Controller):
    @http.route('/smgtyt/smgtyt/', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/smgtyt/smgtyt/objects/', auth='public')
    def list(self, **kw):
        return http.request.render('smgtyt.listing', {
            'root': '/smgtyt/smgtyt',
            'objects': http.request.env['smgtyt.smgtyt'].search([]),
        })

    @http.route('/smgtyt/smgtyt/objects/<model("smgtyt.smgtyt"):obj>/', auth='public')
    def object(self, obj, **kw):
        return http.request.render('smgtyt.object', {
            'object': obj
        })
