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
from openerp.osv import fields, osv
from openerp import netsvc


class pos_order(osv.osv):
    """
    Integration with product_bundle. By Ventura Systems. 

    """

    _inherit = "pos.order"

    def create_picking(self, cr, uid, ids, context=None):
        """
        Create a picking for each order and validate it.

        """

        import ipdb; ipdb.set_trace()
        picking_obj = self.pool.get('stock.picking')
        partner_obj = self.pool.get('res.partner')
        move_obj = self.pool.get('stock.move')

        for order in self.browse(cr, uid, ids, context=context):
            if not order.state=='draft':
                continue
            if order.amount_total >= 0:
                type = 'out'
            else:
                type = 'in'

            addr = order.partner_id and partner_obj.address_get(cr, uid, [order.partner_id.id], ['delivery']) or {}
            picking_id = picking_obj.create(cr, uid, {
                'origin': order.name,
                'partner_id': addr.get('delivery',False),
                'type': type,
                'company_id': order.company_id.id,
                'move_type': 'direct',
                'note': order.note or "",
                'invoice_state': 'none',
                'auto_picking': True,
            }, context=context)
            self.write(cr, uid, [order.id], {'picking_id': picking_id}, context=context)
            location_id = order.shop_id.warehouse_id.lot_stock_id.id
            output_id = order.shop_id.warehouse_id.lot_output_id.id

            for line in order.lines:
                fake_line_ids = []
                is_bundle = False

                if line.product_id.supply_method == 'bundle':
                    fake_line_ids = filter(None, map(lambda x: x, line.product_id.item_ids))
                    is_bundle = True
                else:
                    if line.product_id and line.product_id.type == 'service':
                        continue
                    else:
                        fake_line_ids.append(line)

                for fake_line in fake_line_ids:
                    if not is_bundle:
                        if fake_line.qty < 0:
                            location_id, output_id = output_id, location_id

                        move_obj.create(cr, uid, {
                            'name': fake_line.name,
                            'product_uom': fake_line.product_id.uom_id.id,
                            'product_uos': fake_line.product_id.uom_id.id,
                            'picking_id': picking_id,
                            'product_id': fake_line.product_id.id,
                            'product_uos_qty': abs(fake_line.qty),
                            'product_qty': abs(fake_line.qty),
                            'tracking_id': False,
                            'state': 'draft',
                            'location_id': location_id,
                            'location_dest_id': output_id,
                            'prodlot_id': fake_line.prodlot_id and fake_line.prodlot_id.id or False,
                        }, context=context)
                        if fake_line.qty < 0:
                            location_id, output_id = output_id, location_id
                    else:
                        if fake_line.qty_uom < 0:
                            location_id, output_id = output_id, location_id

                        move_obj.create(cr, uid, {
                            'name': fake_line.item_id.name,
                            'product_uom': fake_line.item_id.uom_id.id,
                            'product_uos': fake_line.item_id.uom_id.id,
                            'picking_id': picking_id,
                            'product_id': fake_line.item_id.id,
                            'product_uos_qty': abs(fake_line.qty_uom),
                            'product_qty': abs(fake_line.qty_uom),
                            'tracking_id': False,
                            'state': 'draft',
                            'location_id': location_id,
                            'location_dest_id': output_id,
                            'prodlot_id': False,
                        }, context=context)
                        if fake_line.qty_uom < 0:
                            location_id, output_id = output_id, location_id

            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
            picking_obj.force_assign(cr, uid, [picking_id], context)
        return True


class pos_order_line(osv.osv):
    _inherit = 'pos.order.line'
    _columns = {
            'appointment_id': fields.many2one(
                'salon.spa.appointment', 'Appointment'),
            # TODO this is needed only if you can cancel pos orders.
            'previous_appointment_id': fields.many2one(
                'salon.spa.appointment', 'Appointment'),
            }
