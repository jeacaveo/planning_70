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
from datetime import datetime, timedelta

from openerp.addons.base_status.base_state import base_state
from openerp.osv.orm import Model
from openerp.osv import fields, osv
from openerp.addons.resource_planning.resource_planning import resource_planning


#order is important here. resource_planning has to come first
class Appointment(resource_planning, base_state, Model):
    _name = 'salon.spa.appointment'

    _resource_fields = ['employee_id', 'space_id']

    _date_field = 'start'

    _duration_field = 'duration'

    _columns = {
            'name': fields.char('Nombre', size=128),
            'start': fields.datetime('Inicio', required=True),
            'duration': fields.float(u'Duración', required=True),
            'price': fields.float(u'Precio'),
            'employee_id': fields.many2one(
                'hr.employee', 'Empleado', required=True),
            'client_id': fields.many2one(
                'res.partner', 'Cliente',
                domain=[('supplier', '=', False)], required=True,),
            'category_id': fields.many2one(
                'product.category', 'Familia',
                domain=[('parent_id', '=', 'Servicios')], required=True),
            'service_id': fields.many2one(
                'salon.spa.service', 'Servicio', required=True),
            'space_id': fields.many2one(
                'salon.spa.space', 'Espacio', required=True),
            'state': fields.selection([('draft', 'Reservada'),
                                       ('pending', 'En Espera'),
                                       ('open', 'Confirmada'),
                                       ('done', 'Concluida'),
                                       ('cancel', 'Cancelada')],
                                       string='Estado', size=16, readonly=True,
                                       track_visibility='onchange',
                                       help="Este estado marca la cita como:\
                                             'Reservada' cuando se crea.\
                                             'En Espera' el dia de la cita,\
                                             y el cliente no ha llegado.\
                                             'Confirmada' el cliente llego.\
                                             'Concluida' la cita concluida.\
                                             'Cancelada' no-show, etc."),
            'notes': fields.text('Notas'),
            'active': fields.boolean('Activo', required=False),
            }

    _defaults = {
            'state': 'draft',
            'active': True
        }

    def onchange_appointment_service(self, cr, uid, ids, service_id, context=None):
        if service_id:
            space_ids = []
            service_object = self.pool.get('salon.spa.service').\
                    browse(cr, uid, service_id, context=context)
            employee_object = self.pool.get('hr.employee').\
                    search(cr, uid, [('service_ids', 'in', service_id)], context=context)

            for space in service_object.space_ids:
                space_available = self.check_availability(cr, uid, ids,\
                                    'space_id', space.id,
                                    context['start_date'], service_object.duration,
                                    context)
                if space_available:
                    space_ids.append(space.id)

            if space_ids:
                assigned_space = space_ids[0]
            else:
                assigned_space = None

            return {
                    'value': {'duration': service_object.duration,
                              'price': service_object.service.list_price,
                              'space_id': assigned_space,
                              'category_id': service_object.categ_id,
                              'employee_id': None
                        },
                    'domain': {'employee_id': [('id', 'in', employee_object)],
                               'space_id': [('id', 'in', space_ids)]
                        },
                   }
        return {'value':
                    {'price': 0,
                     'space_id': None,
                     'duration': 0,
                     'employee_id': None,
                     'category_id': None,
                     }
                }

    def onchange_appointment_start(self, cr, uid, ids, context=None):
        return {'value':
                    {'service_id': None,
                     'space_id': None,
                     'duration': 0,
                     'employee_id': None,
                     'category_id': None,
                     'price': 0,
                     }
                }

    def case_open(self, cr, uid, ids, context=None):
        """ Opens case """
        values = {'active': True}
        return self.case_set(cr, uid, ids, 'open', values, context=context)

    def check_availability(self, cr, uid, ids, resource_type, resource, date, duration, context=None):
        appointment_ids = self.pool.get('salon.spa.appointment').\
                search(cr, uid, [(resource_type, '=', resource)], context=context)

        for appointment in appointment_ids:
            appointment_object = self.pool.get('salon.spa.appointment').\
                    browse(cr, uid, appointment, context=context)
            # appt = appointment
            appt_start_date = datetime.strptime(appointment_object.start, '%Y-%m-%d %H:%M:%S')
            appt_end_date = appt_start_date + (timedelta(hours=appointment_object.duration) )
            new_appt_start_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            if  new_appt_start_date >= appt_start_date and new_appt_start_date < appt_end_date:
                return False
        return True


class Service(Model):
    _inherit = 'resource.resource'

    _name = 'salon.spa.service'

    _columns = {
            'service': fields.many2one(
                'product.product',
                'Nombre',
                domain=[('type', '=', 'service')],
                required=True),
            'duration': fields.float('Tiempo', required=True),
            'categ_id': fields.char('Categoria', required=True),
            'instructions': fields.text('Instrucciones', translate=True),
            'space_ids': fields.many2many(
                'salon.spa.space',
                'service_space_rel',
                'service_id', 'space_id',
                'Espacios Permitidos'),
            }

    _defaults = {
            'resource_type': 'material',
            }

    def onchange_service_service(self, cr, uid, ids, service, context=None):
        if service:
            service_object = self.pool.get('product.product').\
                    browse(cr, uid, service, context=context)
            return {'value':
                        {'name': service_object.name,
                         'categ_id': service_object.categ_id.id,
                             }
                   }
        return {}


class Space(Model):
    _inherit = 'resource.resource'

    _name = 'salon.spa.space'

    _defaults = {
            'resource_type': 'material',
            }


class hr_employee(osv.osv):
    _inherit = 'hr.employee'
    _columns = {
            'service_ids': fields.many2many(
                'salon.spa.service',
                'employee_service_rel',
                'employee_id', 'service',
                'Servicios'),
            }


class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
            'product_unit_equivalent': fields.float(
                'Equivalencia de Unidad',
                help="El equivalente a 1 unidad para el producto. Solo aplica\
                      cuando la Unidad de Medida es distinta de 'Unidad(es)'."
                ),
            }


class product_supplierinfo(osv.osv):
    _inherit = 'product.supplierinfo'
    _columns = {
            'supplier_unit_equivalent': fields.float(
                'Equivalencia de Unidad',
                help="El equivalente a 1 unidad en las ordenes para el\
                      proveedor. Ejemplo: El proveedor suple los productos\
                      en cajas de 24 unidades, este campo debe tener el valor\
                      24 ya que al pedir 1 caja (unidad del proveedor), se\
                      obtienen los productos deseados (24 unidades). El\
                      equivalente a 1 unidad cuando la unidad de medida del\
                      productos es diferente de 'Unidad(es)', lo toma del\
                      campo product_unit_equivalent."
                      ),
            'supplier_unit_equivalent_name': fields.char(
                'Nombre de Equivalencia',
                size=128,
                help="Unidad, Caja, Bote, etc."),
            }
