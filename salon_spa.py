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
from openerp import netsvc


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

    # appt = appointment
    def onchange_appointment_service(self, cr, uid, ids, service_id, context=None):
        """
        Validates if resources (space and employee) are available for the
        time frame selected.

        Assigns first available resource and sets proper domain.

        Assigns prices and duration according to service.

        """

        if service_id:
            service_obj = self.pool.get('salon.spa.service').\
                    browse(cr, uid, service_id, context=context)
            start_date, duration = context['start_date'], service_obj.duration,

            # Space availability validation
            space_ids = []
            for space in service_obj.space_ids:
                space_available = self.check_resource_availability(cr, uid, ids,\
                                    'space_id', space.id, start_date, \
                                    duration, context)
                if space_available:
                    space_ids.append(space.id)
            if space_ids:
                assigned_space = space_ids[0]
            else:
                assigned_space = None

            # Employee availability validation
            employee_obj = self.pool.get('hr.employee').\
                    search(cr, uid, [('service_ids', 'in', service_id)], context=context)
            employee_ids = []
            for employee in employee_obj:
                employee_available = self.check_resource_availability(cr, uid, ids,\
                                    'employee_id', employee, start_date, \
                                    duration, context)
                if employee_available:
                    employee_available = self.check_employee_availability(cr, uid, ids,\
                            employee, start_date, duration, context)
                    if employee_available:
                        employee_ids.append(employee)
            if employee_ids:
                assigned_employee = employee_ids[0]
            else:
                assigned_employee = None

            return {
                    'value': {'duration': duration,
                              'price': service_obj.service.list_price,
                              'space_id': assigned_space,
                              'category_id': service_obj.categ_id,
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

    def onchange_appointment_start(self, cr, uid, ids,
            employee_id, start, duration, context=None):
        """
        Validates appointment when start date changes.

        """

        if employee_id:
            employee_available = self.check_employee_availability(cr, uid, ids,\
                    employee_id, start, duration, context=context)
            if not employee_available:
                self._raise_unavailable(cr, uid, 'hr.employee', employee_id, context)
        return {}

    def case_open(self, cr, uid, ids, context=None):
        """
        Overwrite of base state case open to only change state.
        (Just like the rest of the states)

        Opens case

        """

        values = {'active': True}
        return self.case_set(cr, uid, ids, 'open', values, context=context)

    def _to_datetime(self, date):
        """
        Get a string date in 'YYYY-mm-dd HH:MM:SS' format.
        Return a datetime object of said date. 

        """

        return datetime.strptime(date, '%Y-%m-%d %H:%M:%S')

    def _day_start_end_time(self, date):
        """
        Get a string date in 'YYYY-mm-dd HH:MM:SS' format.
        Return 2 string dates corresponding to the starting and ending hours
        of the day of the original date.

        """

        day_start = datetime.strptime(date, '%Y-%m-%d %H:%M:%S').replace(hour=0, minute=0, second=0)
        day_start = datetime.strftime(day_start, "%Y-%m-%d %H:%M:%S")
        day_end = datetime.strptime(date, '%Y-%m-%d %H:%M:%S').replace(hour=23, minute=59, second=59)
        day_end = datetime.strftime(day_end, "%Y-%m-%d %H:%M:%S")
        return day_start, day_end

    def _raise_unavailable(self, cr, uid, model, ids, context=None):
        model_obj = self.pool.get(model).\
                browse(cr, uid, ids, context=context)
        raise except_orm(_('Error'), _('%s is not '
            'available at this time!') % (
            model_obj.name))

    def _create_update_order_client_day(self, cr, uid, client_id, date, appt_id, service_obj, context=None):
        """
        Creates pos.order for a client in an specified day with an pos.order.line
        that corresponds to the appointment/service.

        If the pos.order exists, it just adds the pos.order.line.

        """

        try:
            day_start, day_end = self._day_start_end_time(date) 
            client_obj = self.pool.get('res.partner').\
                    browse(cr, uid, client_id, context=context)
            # TODO filter by status and dont allow to create a new order if one is unpaid
            order_obj = self.pool.get('pos.order').\
                    search(cr, uid, [('date_order', '>=', day_start),
                                     ('date_order', '<=', day_end),
                                     ('partner_id', '=', client_obj.id)],
                           context=context)
            # Order creation/modification
            if order_obj:
                order_id = order_obj[0]
            else:  # create it
                order_id = self.pool.get('pos.order').create(cr, uid, {
                    'partner_id': client_obj.id,
                    'date_order': date,
                    # TODO get correct session
                    'session_id': 1,
                    })
            # add service to order
            self.pool.get('pos.order.line').create(cr, uid, {
                'order_id': order_id,
                'name': service_obj.service.name,
                'product_id': service_obj.service.id,
                'price_unit': service_obj.service.list_price,
                'appointment_id': appt_id,
                })
            # TODO Limpiar facturas cuando se elimina un appt o servicio
        except:
            return False

        return True

    def action_view_pos_order(self, cr, uid, ids, context=None):
        """
        This function returns an action that displays existing orders
        of the client for the same day of this appointment.
        It can either be in a list,
        or in a form view if there is only one invoice to show.

        """

        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'point_of_sale', 'action_pos_pos_form')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]

        # get orders for the client/day (of appointment)
        appt_obj = self.browse(cr, uid, ids, context=context)[0]
        client_obj = appt_obj.client_id
        day_start, day_end = self._day_start_end_time(appt_obj.start) 
        order_ids = self.pool.get('pos.order').\
                search(cr, uid, [('date_order', '>=', day_start),
                                 ('date_order', '<=', day_end),
                                 ('partner_id', '=', client_obj.id)],
                       context=context)
        result['domain'] = "[('id','=',[" + ','.join(map(str, order_ids)) + "])]"

        # change to form view if theirs only one order for the client/day
        if len(order_ids) == 1:
            result['views'] = [(False, 'form')]
            result['res_id'] = order_ids and order_ids[0] or False
        return result

    def check_resource_availability(self, cr, uid, ids,
            resource_type, resource, start_date, duration, context=None):
        """
        Validates that the specified resource_type/resource is available.

        Either end_date or duration is required. If neither, will return False.

        """

        # TODO REFACTOR all validations related to resource availability can be
        # checked with self._assert_availability/self._check_availability.
        # (Employee work schedule doesn't fit here,
        #  unless modifications are done to those methods.)
        day_start, day_end = self._day_start_end_time(start_date) 
        start_date = self._to_datetime(start_date)
        end_date = start_date + timedelta(hours=duration)

        appt_ids = self.pool.get('salon.spa.appointment').\
                search(cr, uid, [('start', '>=', day_start),
                                 ('start', '<=', day_end),
                                 ('id', '!=', ids),
                                 (resource_type, '=', resource)],
                        context=context)

        for appt in appt_ids:
            appt_obj = self.pool.get('salon.spa.appointment').\
                    browse(cr, uid, appt, context=context)
            appt_start_date = datetime.strptime(appt_obj.start, '%Y-%m-%d %H:%M:%S')
            appt_end_date = appt_start_date + timedelta(hours=appt_obj.duration)
            if  (start_date >= appt_start_date and start_date < appt_end_date) \
                or (end_date > appt_start_date and end_date <= appt_end_date):
                return False
        return True

    def check_employee_availability(self, cr, uid, ids,
            employee_id, start_date, duration, context=None):
        """
        Validates that the employee is able to work at the specified time.

        Either end_date or duration is required. If neither, will return False.

        """

        start_date = self._to_datetime(start_date)
        end_date = start_date + timedelta(hours=duration)

        start_date = fields.datetime.context_timestamp(
                cr, uid, start_date, context=context)
        end_date = fields.datetime.context_timestamp(
                cr, uid, end_date, context=context)

        employee_obj = self.pool.get('hr.employee').\
                browse(cr, uid, employee_id, context=context)
        appt_day_of_week = start_date.weekday()
        appt_start_hour = start_date.hour
        appt_end_hour = end_date.hour + (end_date.minute / 60)  # float format

        # if employee has no work schedule assigned, skip it
        if employee_obj.working_hours:
            for period in employee_obj.working_hours.attendance_ids:
                if int(period.dayofweek) == appt_day_of_week:
                    if appt_start_hour >= period.hour_from \
                        and appt_end_hour <= period.hour_to:
                        return True
        return False

    def write(self, cr, uid, ids, vals, context=None):
        # keys in vals correspond with fields that have changed
        # Get values previous to save
        # prev_appt holds state of appt previous to save
        appt_obj = self.pool.get('salon.spa.appointment').\
                browse(cr, uid, ids[0], context=context)
        prev_appt = {'employee_id': appt_obj.employee_id.id,
                     'start': appt_obj.start,
                     'client_id': appt_obj.client_id.id,
                     'duration': appt_obj.duration,
                     'service_id': appt_obj.service_id.id,
                     }

        service_obj = self.pool.get('salon.spa.service').\
                browse(cr, uid, vals.get('service_id', False) or prev_appt['service_id'], context=context)
        # store read-only fields 
        vals['price'] = service_obj.service.list_price
        vals['duration'] = service_obj.duration

        # Check if client is available for service.
        duration = vals.get('duration', False) or prev_appt['duration']
        client =  vals.get('client_id', False) or prev_appt['client_id']
        start_date = vals.get('start', False) or prev_appt['start']
        client_available = self.check_resource_availability(cr, uid, ids,
                            'client_id', client,
                            start_date, duration=duration, context=context)
        if not client_available:
            self._raise_unavailable(cr, uid, 'res.partner', client, context)

        result = super(Appointment, self).write(cr, uid, ids, vals, context)

        # current_appt holds final state of appt
        # (Take all values not changed from previously saved appt)
        current_appt = {}
        for key, val in vals.iteritems():
            current_appt[key] = val
        for key, val in prev_appt.iteritems():
            if key not in current_appt:
                current_appt[key] = val

        # Check if employee is assigned to service.
        if vals.get('employee_id', False): 
            employee_obj = self.pool.get('hr.employee').\
                    browse(cr, uid, current_appt['employee_id'],
                           context=context)
            service_ids = []
            for service in employee_obj.service_ids:
                service_ids.append(service.id)
            if current_appt['service_id'] not in service_ids:
                raise except_orm(_('Error'), _('%s is not '
                    'assigned to work with %s!') % (
                    employee_obj.name,
                    service_obj.service.name))

        # Duration changes if service is modified
        if vals.get('duration', False): 
            # Validate employee work schedule
            employee_available = self.check_employee_availability(cr, uid, ids,
                    current_appt['employee_id'], current_appt['start'],
                    current_appt['duration'], context)
            if not employee_available:
                self._raise_unavailable(cr, uid, 'hr.employee', current_appt['employee_id'], context)

        # If one of the orders related fields changes
        # (client_id, start, service_id), delete order line for appt.
        # Later an order is created or modificed with the new info.
        if vals.get('client_id', False) \
            or vals.get('start', False) \
            or vals.get('service_id', False):
            if current_appt['client_id'] != prev_appt['client_id'] \
                or datetime.strptime(current_appt['start'], '%Y-%m-%d %H:%M:%S').replace(hour=0, minute=0, second=0) \
                   != datetime.strptime(prev_appt['start'], '%Y-%m-%d %H:%M:%S').replace(hour=0, minute=0, second=0) \
                or current_appt['service_id'] != prev_appt['service_id']:
                order_line_obj = self.pool.get('pos.order.line').\
                        search(cr, uid, [('appointment_id', '=', ids[0])],
                               context=context)
                del_order_line = self.pool.get('pos.order.line').\
                        unlink(cr, uid, order_line_obj[0], context=context)
                if not del_order_line:
                    raise  #TODO proper message
                if not self._create_update_order_client_day(cr, uid, current_appt['client_id'], current_appt['start'], ids[0], service_obj, context=None):
                    raise  #TODO proper message
        return result

    def create(self, cr, uid, vals, context=None):
        service_obj = self.pool.get('salon.spa.service').\
                browse(cr, uid, vals['service_id'], context=context)
        # store read-only fields
        vals['price'] = service_obj.service.list_price
        vals['duration'] = service_obj.duration

        # Check if client is available for service.
        # TODO REFACTOR
        duration = vals.get('duration', False)
        client =  vals.get('client_id', False)
        start_date = vals.get('start', False)
        client_available = self.check_resource_availability(cr, uid, 0, # 0=ids es el id del appointment, pero este no existe aun
                            'client_id', client,
                            start_date, duration, context=context)
        if not client_available:
            self._raise_unavailable(cr, uid, 'res.partner', client, context)

        id = super(Appointment, self).create(cr, uid, vals, context)
        ids = vals

        # Validate employee work schedule
        employee_available = self.check_employee_availability(cr, uid, ids,\
                vals['employee_id'], vals['start'], \
                vals['duration'], context)
        if not employee_available:
            self._raise_unavailable(cr, uid, 'hr.employee', vals['employee_id'], context)

        if not self._create_update_order_client_day(cr, uid, vals['client_id'], vals['start'], id, service_obj, context=None):
            raise  #TODO proper message
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
            product_obj = self.pool.get('product.product').\
                    browse(cr, uid, service, context=context)
            return {'value':
                        {'name': product_obj.name,
                         'categ_id': product_obj.categ_id.id,
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


class pos_order_line(osv.osv):
    _inherit = 'pos.order.line'
    _columns = {
            'appointment_id': fields.many2one(
                'salon.spa.appointment', 'Appointment'),
            # TODO this is needed only if you can cancel pos orders.
            # Not implemented yet.
            'previous_appointment_id': fields.many2one(
                'salon.spa.appointment', 'Appointment'),
            }


class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
            'referrer_id': fields.many2one(
                'res.partner', 'Refered by',
                help='Another client that refered this client.'),
            'reference_used': fields.boolean('Rerefence Used', readonly=True),
            }

    _defaults = {
        'reference_used': False,
        }


# TODO product_bundle integration to pos.order
# This only works for sale.order
class pos_order(osv.osv):
    _inherit = "pos.order"
    
    def _prepare_order_picking(self, cr, uid, order, context=None):
        pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
        return {
            'name': pick_name,
            'origin': order.name,
            'date': order.date_order,
            'type': 'out',
            'state': 'auto',
            'move_type': order.picking_policy,
            'sale_id': order.id,
            'partner_id': order.partner_shipping_id.id,
            'note': order.note,
            'invoice_state': (order.order_policy=='picking' and '2binvoiced') or 'none',
            'company_id': order.company_id.id,
        }
    
    def _create_pickings_and_procurements(self, cr, uid, order, order_lines, picking_id=False, context=None):
        """Create the required procurements to supply sales order lines, also connecting
        the procurements to appropriate stock moves in order to bring the goods to the
        sales order's requested location.

        If ``picking_id`` is provided, the stock moves will be added to it, otherwise
        a standard outgoing picking will be created to wrap the stock moves, as returned
        by :meth:`~._prepare_order_picking`.

        Modules that wish to customize the procurements or partition the stock moves over
        multiple stock pickings may override this method and call ``super()`` with
        different subsets of ``order_lines`` and/or preset ``picking_id`` values.

        :param browse_record order: sales order to which the order lines belong
        :param list(browse_record) order_lines: sales order line records to procure
        :param int picking_id: optional ID of a stock picking to which the created stock moves
                               will be added. A new picking will be created if ommitted.
        :return: True
        """
        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')
        procurement_obj = self.pool.get('procurement.order')
        proc_ids = []
        
        location_id = order.shop_id.warehouse_id.lot_stock_id.id
        output_id = order.shop_id.warehouse_id.lot_output_id.id

        for line in order_lines:
            if line.state == 'done':
                continue

            date_planned = self._get_date_planned(cr, uid, order, line, order.date_order, context=context)
            
            fake_line_ids = []
            is_bundle = False
            
            if line.product_id:
                if line.product_id.supply_method == 'bundle':
                    fake_line_ids = filter(None, map(lambda x:x, line.product_id.item_ids))
                    is_bundle = True
                else:
                    fake_line_ids.append(line)
                
                for fake_line in fake_line_ids:
                    line_vals = {}
                    
                    line_vals.update({
                        'location_id': location_id,
                        'company_id': order.company_id.id,                        
                        #move
                        'location_dest_id': output_id,
                        'date': date_planned,
                        'date_expected': date_planned,
                        'partner_id': line.address_allotment_id.id or order.partner_shipping_id.id,
                        'sale_line_id': line.id,
                        'origin': order.name,
                        'tracking_id': False,
                        'state': 'draft',
                    })
                    
                    if is_bundle:
                        line_vals.update({
                            'product_id': fake_line.item_id.id,
                            'product_qty': fake_line.qty_uom,
                            'product_uom': fake_line.uom_id.id,
                            'product_uos_qty': fake_line.qty_uom,
                            'product_uos': fake_line.uom_id.id,
                            'procure_method': fake_line.item_id.procure_method,
                            'price_unit': fake_line.item_id.standard_price or 0.0,
                            'name': fake_line.item_id.name,
                            'note': fake_line.item_id.name + ' (' + line.name + ')',
                        })
                        product_id = fake_line.item_id
                    else:
                        line_vals.update({
                            'name': line.name,
                            'note': line.name,
                            'product_id': line.product_id.id,
                            'product_qty': line.product_uom_qty,
                            'product_uom': line.product_uom.id,
                            'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
                            'product_uos': (line.product_uos and line.product_uos.id) or line.product_uom.id,
                            'procure_method': line.type,
                            'product_packaging': line.product_packaging,
                            'price_unit': line.product_id.standard_price or 0.0,
                        })
                        product_id = line.product_id
                    
                    
                    if product_id.type in ('product', 'consu'):
                        if not picking_id:
                            picking_id = picking_obj.create(cr, uid, self._prepare_order_picking(cr, uid, order, context=context))
                        line_vals.update({'picking_id': picking_id,})
                        move_id = move_obj.create(cr, uid, line_vals)
                    else:
                        # a service has no stock move
                        move_id = False
                    
                    del line_vals['location_dest_id']
                    del line_vals['date']
                    del line_vals['date_expected']
                    del line_vals['picking_id']
                    del line_vals['partner_id']
                    del line_vals['sale_line_id']
                    del line_vals['tracking_id']
                    del line_vals['state']
                    
                    line_vals.update({
                        'move_id': move_id,
                        'date_planned': date_planned,
                    })
                    
                    proc_id = procurement_obj.create(cr, uid, line_vals)
                    proc_ids.append(proc_id)
                    line.write({'procurement_id': proc_id})
                    self.ship_recreate(cr, uid, order, line, move_id, proc_id)

        wf_service = netsvc.LocalService("workflow")
        if picking_id:
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
        for proc_id in proc_ids:
            wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)

        val = {}
        if order.state == 'shipping_except':
            val['state'] = 'progress'
            val['shipped'] = False

            if (order.order_policy == 'manual'):
                for line in order.order_line:
                    if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                        val['state'] = 'manual'
                        break
        order.write(val)
        return True
    
    
    def action_ship_create(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            self._create_pickings_and_procurements(cr, uid, order, order.order_line, None, context=context)
        return True
    


# Since invoicing is handled by POS instead of sales,
# this modifications are not needed but can be helpful.
#class sale_order(osv.osv):
#    _inherit = 'sale.order'
#    _order = "date_order desc, partner_id"
#
#    def copy(self, cr, uid, id, default=None, context=None):
#        """
#        Overwrite of copy to create a copy with the same date as the old one,
#        and to assign the proper values to appointment_id in sale.order.line.
#
#        """
#
#        prev_order_object = self.pool.get('sale.order').browse(cr, uid, id, context=context)
#        ret = super(sale_order, self).copy(cr, uid, id, default, context=context)
#        self.write(cr, uid, ret, {'date_order': prev_order_object.date_order}, context=context)
#        new_order_object = self.pool.get('sale.order').browse(cr, uid, ret, context=context)
#        order_line_object = self.pool.get('sale.order.line')
#        order_line_object.write(cr, uid, [l.id for l in  new_order_object.order_line],
#                {'appointment_id': l.previous_appointment_id.id,
#                 'previous_appointment_id': None,
#                 })
#        return ret
#
#    def action_cancel(self, cr, uid, ids, context=None):
#        """
#        Overwrite of action_cancel, just to update
#        sale_order_line in appointment_id and  previous_appointment_id
#
#        """
#
#        wf_service = netsvc.LocalService("workflow")
#        if context is None:
#            context = {}
#        sale_order_line_obj = self.pool.get('sale.order.line')
#        for sale in self.browse(cr, uid, ids, context=context):
#            for inv in sale.invoice_ids:
#                if inv.state not in ('draft', 'cancel'):
#                    raise osv.except_osv(
#                        _('Cannot cancel this sales order!'),
#                        _('First cancel all invoices attached to this sales order.'))
#            for r in self.read(cr, uid, ids, ['invoice_ids']):
#                for inv in r['invoice_ids']:
#                    wf_service.trg_validate(uid, 'account.invoice', inv, 'invoice_cancel', cr)
#            sale_order_line_obj.write(cr, uid, [l.id for l in  sale.order_line],
#                    {'state': 'cancel',
#                     'appointment_id': None,
#                     'previous_appointment_id': l.appointment_id.id,
#                     })
#        self.write(cr, uid, ids, {'state': 'cancel'})
#        return True
#
#    def manual_invoice(self, cr, uid, ids, context=None):
#        """
#        Overwrite of manual_invoice to create a validated and paid invoice.
#        (Instead of a draft invoice)
#
#        Original documentation:
#        create invoices for the given sales orders (ids), and open the form
#        view of one of the newly created invoices
#
#        """
#
#        mod_obj = self.pool.get('ir.model.data')
#        wf_service = netsvc.LocalService("workflow")
#
#        # create invoices through the sales orders' workflow
#        inv_ids0 = set(inv.id for sale in self.browse(cr, uid, ids, context) for inv in sale.invoice_ids)
#        for order_id in ids:
#            wf_service.trg_validate(uid, 'sale.order', order_id, 'manual_invoice', cr)
#        inv_ids1 = set(inv.id for sale in self.browse(cr, uid, ids, context) for inv in sale.invoice_ids)
#        # determine newly created invoices
#        new_inv_ids = list(inv_ids1 - inv_ids0)
#
#        for inv_id in new_inv_ids: 
#            if context.get('auto_pay', False):
#                # Validates Invoice
#                wf_service.trg_validate(uid, 'account.invoice', inv_id, 'invoice_open', cr)
#
#                # Pay Invoice
#                invoice_object = self.pool.get('account.invoice').\
#                        browse(cr, uid, inv_id, context=context)
#                move_line_object = self.pool.get('account.move.line').\
#                        search(cr, uid, [('move_id', '=', invoice_object.move_id.id), ('debit', '>', 0)], context=context)
#                voucher_id = self.pool.get('account.voucher').create(cr, uid, {
#                    'partner_id': invoice_object.partner_id.id,
#                    # TODO Pagos Parciales
#                    'amount': invoice_object.amount_total,
#                    # TODO Multiples pagos
#                    'journal_id': context.get('journal_id', False),
#                    'account_id': invoice_object.account_id.id,
#                    'type': 'receipt',
#                    })
#                for move_line in move_line_object:
#                    self.pool.get('account.voucher.line').create(cr, uid, {
#                        'voucher_id': voucher_id,
#                        'name': invoice_object.number,
#                        'partner_id': invoice_object.partner_id.id,
#                        'amount': invoice_object.amount_total,
#                        'account_id': invoice_object.account_id.id,
#                        'move_line_id': move_line,
#                        'type': 'cr',
#                        })
#                wf_service.trg_validate(uid, 'account.voucher', voucher_id, 'proforma_voucher', cr)
#        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
#        res_id = res and res[1] or False,
#
#        return {
#            'name': _('Customer Invoices'),
#            'view_type': 'form',
#            'view_mode': 'form',
#            'view_id': [res_id],
#            'res_model': 'account.invoice',
#            'context': "{'type':'out_invoice'}",
#            'type': 'ir.actions.act_window',
#            'nodestroy': True,
#            'target': 'current',
#            'res_id': new_inv_ids and new_inv_ids[0] or False,
#        }


# Since invoicing is handled by POS instead of sales,
# this modifications are not needed but can be helpful.
#class sale_advance_payment_inv(osv.osv_memory):
#    _inherit = 'sale.advance.payment.inv'
#
#    # TODO This should be done in the context of the action that calls
#    # sale_make_invoice_advance_view or http://forum.openerp.com/forum/topic28369.html
#    def _payment_total(self, cr, uid, ids, context=None):
#        """
#        Shows the order/invoice total.
#
#        """
#
#        cur_obj = self.pool.get('res.currency')
#        res = {}
#        for order in self.browse(cr, uid, ids, context=context):
#            res[order.id] = {
#                'amount_untaxed': 0.0,
#                'amount_tax': 0.0,
#                'amount_total': 0.0,
#            }   
#            val = val1 = 0.0
#            cur = order.pricelist_id.currency_id
#            for line in order.order_line:
#                val1 += line.price_subtotal
#                val += self._amount_line_tax(cr, uid, line, context=context)
#            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
#            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
#            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
#        return res[order.id]['amount_total']
#    
#    _columns = {
#            'advance_payment_method':fields.selection(
#                [('auto_pay', 'Invoice the whole sale plus Payment'),
#                 ('all', 'Invoice the whole sales order'),
#                 ('percentage','Percentage'),
#                 ('fixed','Fixed price (deposit)'),
#                 ('lines', 'Some order lines')
#                 ],
#                'What do you want to invoice?', required=True,
#                help="""Use All to create the final invoice.
#                    Use Percentage to invoice a percentage of the total amount.
#                    Use Fixed Price to invoice a specific amound in advance.
#                    Use Some Order Lines to invoice a selection of the sales order lines."""),
#            'journal_id':fields.many2one('account.journal', 'Journal', help="Payment method for the Invoce."),
#            'payment_amount': fields.float(string='Payment Amount', readonly=True,  help="Total amount for the order/invoice to be paid."),
#            }
#    
#    _defaults = {
#        'advance_payment_method': 'auto_pay',
#        }
#
#    def create_invoices(self, cr, uid, ids, context=None):
#        """
#        Overwrite of method to include 'auto_pay' in same
#        validation as 'all'.
#
#        Original documentation:
#        create invoices for the active sales orders
#        
#        """
#
#        sale_obj = self.pool.get('sale.order')
#        act_window = self.pool.get('ir.actions.act_window')
#        wizard = self.browse(cr, uid, ids[0], context)
#        sale_ids = context.get('active_ids', [])
#        if wizard.advance_payment_method in ['all', 'auto_pay']:
#            # create the final invoices of the active sales orders
#            res = sale_obj.manual_invoice(cr, uid, sale_ids, context)
#            if context.get('open_invoices', False):
#                return res
#            return {'type': 'ir.actions.act_window_close'}
#
#        if wizard.advance_payment_method == 'lines':
#            # open the list view of sales order lines to invoice
#            res = act_window.for_xml_id(cr, uid, 'sale', 'action_order_line_tree2', context)
#            res['context'] = {
#                'search_default_uninvoiced': 1,
#                'search_default_order_id': sale_ids and sale_ids[0] or False,
#            }
#            return res
#        assert wizard.advance_payment_method in ('fixed', 'percentage')
#
#        inv_ids = []
#        for sale_id, inv_values in self._prepare_advance_invoice_vals(cr, uid, ids, context=context):
#            inv_ids.append(self._create_invoices(cr, uid, inv_values, sale_id, context=context))
#
#        if context.get('open_invoices', False):
#            return self.open_invoices( cr, uid, ids, inv_ids, context=context)
#        return {'type': 'ir.actions.act_window_close'}
