# -*- coding: utf-8 -*-

{
    'name': 'Calculo Inverso para Nóminas',
    'summary': 'Calcula el sueldo diario con base en el sueldo neto.',
    'description': '''
    Nomina CFDI Module
    ''',
    'author': 'IT Admin',
    'version': '16.02',
    'category': 'Employees',
    'depends': [
        'base', 'hr', 'om_hr_payroll', 'nomina_cfdi_ee',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_contract_view.xml',
        'wizard/calculo_inverso_view.xml',
        'wizard/genera_nomina_inversa_view.xml'
    ],
    'installable': True,
    'application': False,
    'license': 'AGPL-3',
}
