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
from openerp.tools.translate import _
from openerp.osv.orm import Model, except_orm
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
        """
        Validates if resources (space and employee) are available for the
        time frame selected.

        Assigns first available resource and sets proper domain.

        Assigns prices and duration according to service.

        """

        if service_id:
            service_object = self.pool.get('salon.spa.service').\
                    browse(cr, uid, service_id, context=context)
            date, duration = context['start_date'], service_object.duration,
            start_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            end_date = start_date + timedelta(hours=duration)

            # Space availability validation
            space_ids = []
            for space in service_object.space_ids:
                space_available = self.check_resource_availability(cr, uid, ids,\
                                    'space_id', space.id, start_date, \
                                    end_date, duration, context)
                if space_available:
                    space_ids.append(space.id)
            if space_ids:
                assigned_space = space_ids[0]
            else:
                assigned_space = None

            # Employee availability validation
            employee_object = self.pool.get('hr.employee').\
                    search(cr, uid, [('service_ids', 'in', service_id)], context=context)
            employee_ids = []
            for employee in employee_object:
                employee_available = self.check_resource_availability(cr, uid, ids,\
                                    'employee_id', employee, start_date, \
                                    end_date, duration, context)
                if employee_available:
                    employee_available = self.check_employee_availability(cr, uid, ids,\
                            employee, start_date, end_date, duration, context)
                    if employee_available:
                        employee_ids.append(employee)
            if employee_ids:
                assigned_employee = employee_ids[0]
            else:
                assigned_employee = None

            return {
                    'value': {'duration': duration,
                              'price': service_object.service.list_price,
                              'space_id': assigned_space,
                              'category_id': service_object.categ_id,
                              'employee_id': assigned_employee
                        },
                    'domain': {'employee_id': [('id', 'in', employee_ids)],
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
        """
        Resets all fields when start date changes.

        """

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
        """
        Re-write of base state case open to only change state.
        (Just like the rest of the states)

        Opens case

        """

        values = {'active': True}
        return self.case_set(cr, uid, ids, 'open', values, context=context)

    def check_resource_availability(self, cr, uid, ids, resource_type, resource, \
            start_date, end_date=None, duration=None, context=None):
        """
        Validates that the specified resource_type/resource is available.

        Either end_date or duration is required. If neither, will return False.

        """

        # TODO REFACTOR all validations related to resource availability can be
        # checked with self._assert_availability/self._check_availability.
        # (Employee work schedule doesn't fit here,
        #  unless modifications are done to those methods.)
        if not end_date:
            if duration:
                end_date = start_date + timedelta(hours=duration)
            else:
                return False
        appointment_ids = self.pool.get('salon.spa.appointment').\
                search(cr, uid, [(resource_type, '=', resource)],
                        context=context)

        for appointment in appointment_ids:
            appointment_object = self.pool.get('salon.spa.appointment').\
                    browse(cr, uid, appointment, context=context)
            # appt = appointment
            appt_start_date = datetime.strptime(appointment_object.start, '%Y-%m-%d %H:%M:%S')
            appt_end_date = appt_start_date + timedelta(hours=appointment_object.duration)
            if  (start_date >= appt_start_date and start_date < appt_end_date) \
                or (end_date > appt_start_date and end_date <= appt_end_date):
                return False
        return True

    def check_employee_availability(self, cr, uid, ids, employee_id, start_date,
            end_date=None, duration=None, context=None):
        """
        Validates that the employee is able to work at the specified time.

        Either end_date or duration is required. If neither, will return False.

        """

        if not end_date:
            if duration:
                end_date = start_date + timedelta(hours=duration)
            else:
                return False
        start_date = fields.datetime.context_timestamp(
                cr, uid, start_date, context=context)
        end_date = fields.datetime.context_timestamp(
                cr, uid, end_date, context=context)

        employee_object = self.pool.get('hr.employee').\
                browse(cr, uid, employee_id, context=context)
        appt_day_of_week = start_date.weekday()
        appt_start_hour = start_date.hour
        appt_end_hour = end_date.hour + (end_date.minute / 60)  # float format

        # if employee has no work schedule assigned, skip it
        if employee_object.working_hours:
            # appt = appointment
            for period in employee_object.working_hours.attendance_ids:
                if int(period.dayofweek) == appt_day_of_week:
                    if appt_start_hour >= period.hour_from \
                        and appt_end_hour <= period.hour_to:
                        return True
        return False

    def write(self, cr, uid, ids, vals, context=None):
        # appt = appointment
        # Get values previous to save
        # prev_appt holds state of appt previous to save
        appointment_object = self.pool.get('salon.spa.appointment').\
                browse(cr, uid, ids[0], context=context)
        prev_appt = {'employee_id': appointment_object.employee_id.id,
                     'start': appointment_object.start,
                     'client_id': appointment_object.client_id.id,
                     'duration': appointment_object.duration,
                     'service_id': appointment_object.service_id.id,
                     }

        result = super(Appointment, self).write(cr, uid, ids, vals, context)

        # current_appt holds final state of appt
        # (Take all values not changed from previously saved appt)
        current_appt = {}
        for key, val in vals.iteritems():
            current_appt[key] = val
        for key, val in prev_appt.iteritems():
            if key not in current_appt:
                current_appt[key] = val

        # Duration changes if date, service or duration is modified
        if 'duration' in vals:
            # TODO refactor to avoid repetition
            # Validate employee work schedule
            start_date = datetime.strptime(current_appt['start'], '%Y-%m-%d %H:%M:%S')
            end_date = start_date + timedelta(hours=current_appt['duration'])
            employee_available = self.check_employee_availability(cr, uid, ids,\
                    current_appt['employee_id'], start_date, \
                    end_date, current_appt['duration'], context)
            if not employee_available:
                employee_object = self.pool.get('hr.employee').\
                        browse(cr, uid, current_appt['employee_id'],
                               context=context)
                raise except_orm(_('Error'), _('%s is not '
                    'programmed to work at this time!') % (
                    employee_object.name))

        # If one of the invoice related fields changes
        # (client_id, start, service_id), delete invoice line for appt.
        # Later an invoice is created or modificed with the new info.
        if 'client_id' in vals \
            or 'start' in vals \
            or 'service_id' in vals:
            if current_appt['client_id'] != prev_appt['client_id'] \
                or current_appt['start'] != prev_appt['start'] \
                or current_appt['service_id'] != prev_appt['service_id']:
                invoice_line_object = self.pool.get('account.invoice.line').\
                        search(cr, uid, [('appointment_id', '=', ids[0])],
                               context=context)
                del_invoice_line = self.pool.get('account.invoice.line').\
                        unlink(cr, uid, invoice_line_object[0], context=context)
                if not del_invoice_line:
                    raise

        # TODO refactor to avoid repetition
        # Look for an existing invoice for client/date
        client_object = self.pool.get('res.partner').\
                browse(cr, uid, current_appt['client_id'], context=context)
        invoice_object = self.pool.get('account.invoice').\
                search(cr, uid,
                       [('date_invoice', '=', current_appt['start']),
                        ('partner_id', '=', client_object.id)],
                       context=context)

        # Invoice creation/modification
        if invoice_object:
            invoice_id = invoice_object[0]
        else:  # create it
            invoice_id = self.pool.get('account.invoice').create(cr, uid, {
                'partner_id': client_object.id,
                'date_invoice': current_appt['start'],
                'account_id': client_object.property_account_receivable.id,
                })
        # add service to invoice
        service_object = self.pool.get('salon.spa.service').\
                browse(cr, uid, current_appt['service_id'], context=context)
        self.pool.get('account.invoice.line').create(cr, uid, { \
            'invoice_id': invoice_id, \
            'name': service_object.service.name, \
            'product_id': service_object.service.id, \
            'price_unit': service_object.service.list_price, \
            'appointment_id': ids[0], \
            })

        # Si se elimina o cancela la cita
            # eliminar servicio de factura del cliente
        # Luego de cada eliminacion de servicio, se valida si
        # la factura no tiene servicios. Se elimina factura si es asi.

        return result

    def create(self, cr, uid, vals, context=None):
        id = super(Appointment, self).create(cr, uid, vals, context)

        ids = vals

        # TODO refactor to avoid repetition
        # Validate employee work schedule
        start_date = datetime.strptime(vals['start'], '%Y-%m-%d %H:%M:%S')
        end_date = start_date + timedelta(hours=vals['duration'])
        employee_available = self.check_employee_availability(cr, uid, ids,\
                vals['employee_id'], start_date, \
                end_date, vals['duration'], context)
        if not employee_available:
            employee_object = self.pool.get('hr.employee').\
                    browse(cr, uid, vals['employee_id'], context=context)
            raise except_orm(_('Error'), _('%s is not '
                'programmed to work at this time!') % (
                employee_object.name))

        # TODO refactor to avoid repetition
        # Invoice creation/modification
        appointment_date = vals['start']
        client_object = self.pool.get('res.partner').\
                browse(cr, uid, vals['client_id'], context=context)
        invoice_object = self.pool.get('account.invoice').\
                search(cr, uid, [('date_invoice', '=', appointment_date),
                                 ('partner_id', '=', client_object.id)],
                       context=context)
        if invoice_object:
            invoice_id = invoice_object[0]
        else:  # create it
            invoice_id = self.pool.get('account.invoice').create(cr, uid, {
                'partner_id': client_object.id,
                'date_invoice': appointment_date,
                'account_id': client_object.property_account_receivable.id,
                })
        # add service to invoice
        service_object = self.pool.get('salon.spa.service').\
                browse(cr, uid, vals['service_id'], context=context)
        self.pool.get('account.invoice.line').create(cr, uid, { \
            'invoice_id': invoice_id, \
            'name': service_object.service.name, \
            'product_id': service_object.service.id, \
            'price_unit': service_object.service.list_price, \
            'appointment_id': id, \
            })

        return id


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
            product_object = self.pool.get('product.product').\
                    browse(cr, uid, service, context=context)
            return {'value':
                        {'name': product_object.name,
                         'categ_id': product_object.categ_id.id,
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
            'working_hours': fields.many2one(
                'resource.calendar',
                'Horario de Trabajo'),
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


class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'
    _columns = {
            'appointment_id': fields.many2one(
                'salon.spa.appointment', 'Appointment'),
            }
