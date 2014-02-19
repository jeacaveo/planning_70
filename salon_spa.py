# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2013 Jean Ventura (<http://venturasystems.net>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv.orm import Model
from openerp.osv import fields
from openerp.addons.resource_planning.resource_planning import resource_planning


#order is important here. resource_planning has to come first
class Appointment(resource_planning, Model):
    _name = 'salon.spa.appointment'

    _resource_fields = ['employee_id', 'space_id']

    _date_field = 'start'

    _duration_field = 'duration'

    _columns = {
            'name': fields.char('Nombre', size=128),
            'start': fields.datetime('Inicio', required=True),
            'duration': fields.float(u'Duración', required=True),
            'employee_id': fields.many2one(
                'hr.employee', 'Empleado', required=True),
            'client_id': fields.many2one(
                'res.partner', 'Cliente',
                domain=[('supplier', '=', False)], required=True,),
            'category_id': fields.many2one(
                'product.category', 'Tipo de Servicio',
                domain=[('parent_id', '=', 'Servicios')], required=True),
            'service_id': fields.many2one(
                'salon.spa.service', 'Servicio', required=True),
            'space_id': fields.many2one(
                'salon.spa.space', 'Espacio', required=True),
            }

    def onchange_appointment_service(self, cr, uid, ids, service_id, context=None):
        if service_id:
            service_object = self.pool.get('salon.spa.service').browse(cr, uid, service_id, context=context)
            return {'value': {'duration': service_object.duration}}
        return {}

    def onchange_appointment_category(self, cr, uid, ids, category_id, context=None):
        if category_id:
            return {'value': 
                        {'service_id': None,
                         'space_id': None,
                         'duration': None,
                         }
                    }
        return {}


class Service(Model):
    _inherit = 'resource.resource'

    _name = 'salon.spa.service'

    _columns = {
            'service': fields.many2one('product.product', 'Nombre', domain=[('type', '=', 'service')], required=True),
            'duration': fields.float('Tiempo', required=True),
            'categ_id': fields.char('Categoria', required=True),
            'instructions': fields.text('Instrucciones', translate=True),
            }

    _defaults = {
            'resource_type': 'material',
            }

    def onchange_service_service(self, cr, uid, ids, service, context=None):
        if service:
            service_object = self.pool.get('product.product').browse(cr, uid, service, context=context)
            return {'value':
                        {'name': service_object.name,
                         'categ_id': service_object.categ_id.id,
                        }
                    }
        return {}


class Space(Model):
    _inherit = 'resource.resource'

    _name = 'salon.spa.space'

    _columns = {
            'category_id': fields.many2one(
                'product.category', 'Tipo de Servicio',
                domain=[('parent_id', '=', 'Servicios')], required=True),
            }

    _defaults = {
            'resource_type': 'material',
            }
