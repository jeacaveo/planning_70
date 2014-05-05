# -*- coding: utf-8 -*-
from openerp.tests import common
from openerp.osv.orm import except_orm


class TestSalonSpa(common.TransactionCase):
    # Refactor to avoid repetition from test_schedule.py
    def create_sched(self, cr, uid, model_obj, date, context=None):
        """
        Helper to create schedules.

        """

        values = {'date': date, 'hour_start': 9, 'hour_end': 21}
        return model_obj.create(cr, uid, values)

    def create_appt(self, cr, uid, model_obj,
            client_id, start, service_id, employee_id=None, context=None):
        """
        Helper to create appointments.

        appt = appointment

        """

        # Create schedule for all employees
        employee_ids = self.employee_obj.search(cr, uid, [], context=context)
        sched_obj = self.sched_obj.browse(cr, uid, self.sched_id)
        for employee in employee_ids:
            employee_obj = self.employee_obj.browse(cr, uid, employee, context=context)
            values = {'employee_id': employee_obj.id, 'hour_start': 9, 'hour_end': 19, 'schedule_id': sched_obj.id}
            self.sched_line_obj.create(cr, uid, values)

        # TODO get real id sequence
        ids = self.appt_obj.search(cr, uid, [],
                order='create_date desc', context=context)
        ids = ids[0] + 1
        onchange_values = model_obj.onchange_appointment_service(cr, uid, ids, service_id, employee_id, context=context)['value']
        values = {'client_id': client_id,
                  'start': start,
                  'service_id': service_id,
                  'duration': onchange_values['duration'],
                  'price': onchange_values['price'],
                  'space_id': employee_id or onchange_values['space_id'],
                  'employee_id': onchange_values['employee_id']
                  }
        return model_obj.create(cr, uid, values)

    def setUp(self):
        super(TestSalonSpa, self).setUp()

        # Cursor and user initialization
        cr, uid = self.cr, self.uid

        # Modules to test
        # appt = appointment
        self.appt_obj = self.registry('salon.spa.appointment')
        self.pos_order_obj = self.registry('pos.order')
        self.pos_order_line_obj = self.registry('pos.order.line')
        self.sched_obj = self.registry('salon.spa.schedule')
        self.sched_line_obj = self.registry('salon.spa.schedule.line')
        self.employee_obj = self.registry('hr.employee')

        # Positive tests data
        date = '2000-01-01'
        self.sched_id = self.create_sched(cr, uid, self.sched_obj, date)

        client_id = 68
        # TODO fix timezone problem (this time is actually 12:30)
        self.start = '2000-01-01 16:30:00'
        self.service_id =  25
        self.appt_id = self.create_appt(cr, uid, self.appt_obj,
                                        client_id,
                                        self.start,
                                        self.service_id,
                                        context={'tz': 'America/Santo_Domingo',
                                                 'start_date': self.start})

        # Negative tests data

    def testAppointmentCancel(self):
        """
        Check canceling appointment changes it to proper status,
        removes pos.order.line if it exists and doesn't allow modifications.

        Also validate that it won't allow pos.order.line unlinking,
        if an appointment_id is present.

        """

        # TODO use receptionist user
        cr, uid = self.cr, 5  # self.uid
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        appt.action_check_in()
        # Validate pos.order.line can't be removed if it's related to an appt.
        order_line_obj = self.pos_order_line_obj.browse(cr, uid, appt.order_line_id.id)
        with self.assertRaises(except_orm) as ex:
            order_line_obj.unlink()
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        appt.action_cancel()
        self.assertTrue(appt.state == 'cancel')
        # Validates modifications are not allowed after cancel
        with self.assertRaises(except_orm) as ex:
            appt.write({'duration': 0})
        # Validate pos.order.line is unlinked after appt is cancelled.
        order_line_obj = self.pos_order_line_obj.browse(cr, uid, appt.order_line_id.id)
        self.assertFalse(order_line_obj.id)
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        self.assertFalse(appt.order_line_id.id)

    def testAppointmentOverCanceled(self):
        """
        Check that you can create and appointment on top of a canceled one,
        with the same resources.
        
        """

        cr, uid = self.cr, self.uid
        appt_cancel = self.appt_obj.browse(cr, uid, self.appt_id)
        appt_cancel.action_cancel()
        appt_id = self.create_appt(cr, uid, self.appt_obj,
                                   appt_cancel.client_id.id,
                                   appt_cancel.start,
                                   appt_cancel.service_id.id,
                                   context={'tz': 'America/Santo_Domingo',
                                            'start_date': self.start})
        appt = self.appt_obj.browse(cr, uid, appt_id)
        self.assertTrue(appt.id)

    def testClientAvailability(self):
        """
        Check that the same client can't have two appointments
        at the same time.
        
        """

        cr, uid = self.cr, self.uid
        first_appt = self.appt_obj.browse(cr, uid, self.appt_id)
        appt_id = None
        with self.assertRaises(except_orm) as ex:
            appt_id = self.create_appt(cr, uid, self.appt_obj,
                                       first_appt.client_id.id,
                                       self.start,
                                       self.service_id,
                                       context={'tz': 'America/Santo_Domingo',
                                                'start_date': self.start})
        appt = self.appt_obj.browse(cr, uid, appt_id)
        self.assertFalse(appt)

    def testEmployeeAvailability(self):
        """
        Check that the same employee can't have two appointments
        at the same time.
        
        """

        cr, uid = self.cr, self.uid
        first_appt = self.appt_obj.browse(cr, uid, self.appt_id)
        client_id = 33
        appt_id = self.create_appt(cr, uid, self.appt_obj,
                                   client_id,
                                   self.start,
                                   self.service_id,
                                   context={'tz': 'America/Santo_Domingo',
                                            'start_date': self.start})
        appt = self.appt_obj.browse(cr, uid, appt_id)
        with self.assertRaises(except_orm) as ex:
            appt.write({'employee_id': first_appt.employee_id.id})
        self.assertTrue(appt.employee_id.id == first_appt.employee_id.id)

    def testSpaceAvailability(self):
        """
        Check that the same space can't have two appointments
        at the same time.
        
        """

        cr, uid = self.cr, self.uid
        first_appt = self.appt_obj.browse(cr, uid, self.appt_id)
        client_id = 33
        appt_id = self.create_appt(cr, uid, self.appt_obj,
                                   client_id,
                                   self.start,
                                   self.service_id,
                                   context={'tz': 'America/Santo_Domingo',
                                            'start_date': self.start})
        appt = self.appt_obj.browse(cr, uid, appt_id)
        with self.assertRaises(except_orm) as ex:
            appt.write({'space_id': first_appt.space_id.id})
        self.assertTrue(appt.space_id.id == first_appt.space_id.id)

    def testAppointmentUnlink(self):
        """
        Check a normal user can't unlink/delete an appointment.
        
        """

        # TODO use receptionist user
        cr, uid = self.cr, 5  # self.uid
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        
        with self.assertRaises(except_orm) as ex:
            appt.unlink()
        self.assertTrue(appt.id)

    def testAppointmentUnlinkManager(self):
        """
        Check a manager user can unlink/delete an appointment.
        
        """

        cr, uid = self.cr, self.uid
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        self.assertTrue(appt.unlink())

    def testAppointmentDone(self):
        """
        Pay the POS order for a checked-in appointment,
        and validate that appointment status has changed and can't be modified.
        
        """

        # TODO use receptionist user
        cr, uid = self.cr, 5  # self.uid
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        appt.action_check_in()
        self.assertTrue(appt.state == 'open')
        order_obj = self.pos_order_obj.browse(cr, uid, appt.order_line_id.order_id.id)
        self.assertTrue(order_obj.id)
        order_obj.action_create_invoice()
        self.assertTrue(order_obj.state == 'invoiced')
        invoice_obj = order_obj.invoice_id
        self.assertTrue(invoice_obj.state == 'open')
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        self.assertTrue(appt.state == 'done')
        with self.assertRaises(except_orm) as ex:
            appt.write({'duration': 999})
        # Only manager users can unlink
        cr, uid = self.cr, self.uid
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        with self.assertRaises(except_orm) as ex:
            appt.unlink()
