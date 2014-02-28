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
            'price': fields.float(u'Precio', required=True),
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
            'state': fields.selection([('draft', 'Reservada'),
                                       ('pending', 'En Espera'),
                                       ('open', 'Confirmada'),
                                       ('done', 'Concluida'),
                                       ('cancel', 'Cancelada')],
                                       string='Estado', size=16, readonly=True, track_visibility='onchange',
                                       help="Este estado marca la cita como:\
                                             'Reservada' cuando se crea.\
                                             'En Espera'cuando es el dia de la cita,\
                                             y el cliente no ha llegado.\
                                             'Confirmada' cuando el cliente ha llegado.\
                                             'Concluida' cuando la cita termina.\
                                             'Cancelada' cuando el cliente no llega o cancela."),
            'notes': fields.text('Notas'),
            'active': fields.boolean('Activo', required=False),
            }
    

    _defaults = {
            'state': 'draft',
            'active': True
        }

    def onchange_appointment_service(self, cr, uid, ids, service_id, context=None):
        if service_id:
            service_object = self.pool.get('salon.spa.service').browse(cr, uid, service_id, context=context)
            employee_object = self.pool.get('hr.employee').search(cr, uid, [('service_ids', 'in', service_id)], context=context)
            return {
                    'value': {'duration': service_object.duration,
                              'price': service_object.service.list_price},
                    'domain': {'employee_id': [('id', 'in', employee_object)]},
                   }
        return {}

    def onchange_appointment_category(self, cr, uid, ids, category_id, context=None):
        if category_id:
            return {'value': 
                        {'service_id': None,
                         'space_id': None,
                         'duration': None,
                         'employee_id': None,
                         }
                    }
        return {}

    def case_open(self, cr, uid, ids, context=None):
        """ Opens case """
        values = {'active': True}
        return self.case_set(cr, uid, ids, 'open', values, context=context)

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


class hr_employee(osv.osv):
    _inherit = 'hr.employee'
    _columns = { 
            'service_ids': fields.many2many('salon.spa.service', 'employee_service_rel', 'employee_id','service', 'Servicios'),
            }


class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
            'product_unit_equivalent': fields.float('Equivalencia de Unidad',
                help="El equivalente a 1 unidad para este producto. Solo aplica\
                      cuando la Unidad de Medida es distinta de 'Unidad(es)'."
                ),
            }


class product_supplierinfo(osv.osv):
    _inherit = 'product.supplierinfo'
    _columns = {
            'supplier_unit_equivalent': fields.float('Equivalencia de Unidad',
                help="El equivalente a 1 unidad en las ordenes para el\
                      proveedor. Ejemplo: El proveedor suple los productos\
                      en cajas de 24 unidades, este campo debe tener el valor\
                      24 ya que al pedir 1 caja (unidad del proveedor), se\
                      obtienen los productos deseados (24 unidades). El\
                      equivalente a 1 unidad cuando la unidad de medida del\
                      productos es diferente de 'Unidad(es)', lo toma del\
                      campo product_unit_equivalent."
                      ),
            'supplier_unit_equivalent_name': fields.char('Nombre de Equivalencia', size=128, help="Unidad, Caja, Bote, etc."),
            }
