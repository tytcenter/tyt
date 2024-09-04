# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class Employee(models.Model):
    _inherit = "hr.employee"

    unidadmedicina = fields.Char(_('Unidad de medicina familiar'))
    no_guia = fields.Char(_('Clave subdelegación (2 dígitos)'))

    tipodetrabajador = fields.Selection(
        selection=[('1', '1 - Trabajador permanente'),
                   ('2', '2 - Trabajador Ev. en ciudad'),
                   ('3', '3 - Trabajador Ev. en construccion'),
                   ('4', '4 - Eventual de campo'),],
        string=_('Tipo de trabajador'),
    )
    tipodesalario = fields.Selection(
        selection=[('0', '0 - Salario fijo'),
                   ('1', '1 - Salario variable'),
                   ('2', '2 - Salario mixto'),],
        string=_('Tipo de salario'),
    )
    tipodejornada = fields.Selection(
        selection=[('1', '1 - Un dia'),
                   ('2', '2 - Dos dias'),
                   ('3', '3 - Tres dias'),
                   ('4', '4 - Cuatro dias'),
                   ('5', '5 - Cinco dias'),
                   ('6', '6 - Jornada reducida'),
                   ('0', '0 - Jornada normal'),],
        string=_('Tipo de jornada'),
    )
    codigo_postal = fields.Char(_('CP domicilio trabajador'))

class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    unidadmedicina = fields.Char(_('Unidad de medicina familiar'))
    no_guia = fields.Char(_('Clave subdelegación (2 dígitos)'))

    tipodetrabajador = fields.Selection(
        selection=[('1', '1 - Trabajador permanente'),
                   ('2', '2 - Trabajador Ev. en ciudad'),
                   ('3', '3 - Trabajador Ev. en construccion'),
                   ('4', '4 - Eventual de campo'),],
        string=_('Tipo de trabajador'),
    )
    tipodesalario = fields.Selection(
        selection=[('0', '0 - Salario fijo'),
                   ('1', '1 - Salario variable'),
                   ('2', '2 - Salario mixto'),],
        string=_('Tipo de salario'),
    )
    tipodejornada = fields.Selection(
        selection=[('1', '1 - Un dia'),
                   ('2', '2 - Dos dias'),
                   ('3', '3 - Tres dias'),
                   ('4', '4 - Cuatro dias'),
                   ('5', '5 - Cinco dias'),
                   ('6', '6 - Jornada reducida'),
                   ('0', '0 - Jornada normal'),],
        string=_('Tipo de jornada'),
    )
    codigo_postal = fields.Char(_('CP domicilio trabajador'))
