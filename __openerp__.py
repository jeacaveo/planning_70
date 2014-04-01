# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2013 Jean Ventura (<http://venturasystems.net>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name" : "Salon and Spa",
    "version" : "0.4.1",
    "author" : "Ventura Systems",
    "licence": "AGPL v3",
    "complexity": "normal",
    "description": """
    Required:
    Change addons/product/product_data.xml:
        Replace line 3 <data noupdate="1"> with <data>

    For breaks configuration:
        Create a 'Breaks' Product Category.
        Create a 'Break' and a 'Lunch' Product.
        Create a Service for each Product.
        Update both Services to have 'unlimited' time_efficiency:
            update salon_spa_service set time_efficiency = 99  where id = service_id;
        Create a 'Free' Space.
        Update Space to have 'unlimited' time_efficiency:
            update salon_spa_space set time_efficiency = 99  where id = service_id;
        Use a fictional Client for breaks.

    For color configuration:
        Change color_map dict in salon_spa/static/src/jc/salon_spa.js.
        Key is the category_id of the appointment/service.

    """,
    "category" : "",
    "depends" : [
        'hr',
        'point_of_sale',
        'resource_planning',
        'product_bundle',
        'marcos_ncf',
    ],
    "data" : [
        'security/salon_spa_security.xml',
        'security/ir.model.access.csv',
        'salon_spa_view.xml',
        'hr_employee/hr_employee_view.xml',
        'product/product_view.xml',
        'res_partner/res_partner_view.xml',
        'point_of_sale/point_of_sale_view.xml',
    ],
    "js": [
        'static/src/js/salon_spa.js',
    ],
    "css": [
    ],
    'qweb' : [
        'static/src/xml/*.xml',
    ],
    "auto_install": False,
    "installable": True,
    "external_dependencies" : {
        'python' : [],
    },
}
