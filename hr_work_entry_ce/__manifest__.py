#-*- coding:utf-8 -*-

{
    'name': 'HR Work Entries Community',
    'category': 'Generic Modules/Human Resources',
    'author': 'IT Admin',
    'version': '16.01',
    'sequence': 1,
    'website': 'https://www.itadmin.com.mx',
    'summary': 'Funcionalidades para menus de work entries.',
    'description': """Funcionalidades para menus de work entries.""",
    'depends': [
        'om_hr_payroll', 'hr_work_entry', 'hr_work_entry_contract', 'hr_work_entry_holidays', 'hr_work_entry_contract_attendance',
    ],
    'data': [
        'data/hr_payroll_data.xml',
        'views/hr_work_entry_menu.xml',
    ],
    'application': True,
}
