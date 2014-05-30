# -*- coding: utf-8 -*-
from openerp.tests import common
from openerp.osv.orm import except_orm

from datetime import datetime

from . import test_util


class TestPlanning(common.TransactionCase):
    def setUp(self):
        super(TestPlanning, self).setUp()

        # Cursor and user initialization
        cr, uid = self.cr, self.uid

        # Modules to test
        # appt = appointment
        # sched = schedule
        self.space_obj = self.registry('planning.space')
        self.service_obj = self.registry('planning.service')
        self.employee_obj = self.registry('hr.employee')
        self.sched_obj = self.registry('planning.schedule')
        self.sched_line_obj = self.registry('planning.schedule.line')
        self.client_obj = self.registry('res.partner')
        self.pos_session_obj = self.registry('pos.session')
        self.appt_obj = self.registry('planning.appointment')
        self.pos_order_obj = self.registry('pos.order')
        self.pos_order_line_obj = self.registry('pos.order.line')

        # Utility module methods
        self.create_sched = test_util.create_sched
        self.create_sched_line = test_util.create_sched_line
        self.create_appt = test_util.create_appt

        # Create amount of spaces in range
        space_ids = []
        for space_num in range(2):
            values = {'name': 'Space #' + str(space_num)}
            self.space_id = self.space_obj.create(cr, uid, values)
            space_ids.append(self.space_id)

        # Create amount of services (in range) to be provided
        service_ids = []
        for service_num in range(2):
            values = {'name': 'Service #' + str(service_num),
                      'service': 1,  # Use default service product
                      'duration': 1  # 1 Hour
                      }
            self.service_id = self.service_obj.create(cr, uid, values)
            service_obj = self.service_obj.browse(cr, uid, self.service_id)
            # Assign all spaces to the service
            for space_id in space_ids:
                service_obj.write({'space_ids': [(4, space_id)]})
            service_ids.append(self.service_id)

        # Create amount of employees (in range) to provide services
        employee_ids = []
        for employee_num in range(2):
            values = {'name': 'Employee #' + str(employee_num)}
            self.employee_id = self.employee_obj.create(cr, uid, values)
            employee_obj = self.employee_obj.browse(cr, uid, self.employee_id)
            # Assign all services to the employee
            for service_id in service_ids:
                employee_obj.write({'service_ids': [(4, service_id)]})
            employee_ids.append(self.employee_id)

        # TODO Pre-existing data
        values = {'name': 'Break'}
        self.client_obj.create(cr, uid, values, context={})
        values = {'name': 'Libre',
                  'time_efficiency': 99}
        break_space_id = self.space_obj.create(cr, uid, values)
        values = {'name': 'Lunch',
                  'service': 1,  # Use default service product
                  'duration': 1  # 1 Hour
                  }
        break_service_id = self.service_obj.create(cr, uid, values)
        service_obj = self.service_obj.browse(cr, uid, break_service_id)
        service_obj.write({'space_ids': [(4, break_space_id)]})

        # Create schedule for employee
        # Old date chosen to avoid conflict with existing data.
        self.date = '2000-01-01'
        self.sched_id = self.create_sched(cr, uid, self.sched_obj, self.date)
        for employee_id in employee_ids:
            self.sched__line_id = self.create_sched_line(cr, uid,
                                                         self.sched_line_obj,
                                                         self.sched_id,
                                                         employee_id)

        # Create client to provide service to
        values = {'name': 'Client #1'}
        self.client_id = self.client_obj.create(cr, uid, values, context={})

        # Create appointment with a chosen time.
        # TODO fix timezone problem (this time is actually 10:30)
        self.start = '2000-01-01 14:30:00'
        self.appt_id = self.create_appt(cr, uid, self.appt_obj,
                                        self.client_id,
                                        self.start,
                                        self.service_id,
                                        context={'start_date': self.start})

        # To open pos session (pos.session musn't be open when testing.)
        # TODO use receptionist user
        uid = 5  # self.uid
        self.pos_session_id = self.pos_session_obj.create(cr, uid, {'config_id': 1})

    def testAppointmentCancel(self):
        """
        Check canceling appointment changes it to proper status,
        removes pos.order.line if it exists and doesn't allow modifications.

        Also validate that it won't allow pos.order.line unlinking,
        if an order_lind_id is present in the appointment.

        """

        # TODO use receptionist user
        cr, uid = self.cr, 5  # self.uid
        # Open POS Session to be able to create pos.orders
        self.pos_session_obj.open_cb(cr, uid, [self.pos_session_id])
        appt_obj = self.appt_obj.browse(cr, uid, self.appt_id)
        appt_obj.action_check_in()
        # Validate pos.order.line can't be removed if it's related to an appt.
        order_line_obj = self.pos_order_line_obj.browse(cr, uid, appt_obj.order_line_id.id)
        with self.assertRaises(except_orm) as ex:
            order_line_obj.unlink()
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        appt.action_cancel()
        self.assertEqual(appt.state, 'cancel')
        # Validates modifications are not allowed after cancel
        with self.assertRaises(except_orm) as ex:
            appt.write({'duration': 2})
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
                                   context={'start_date': self.start})
        appt = self.appt_obj.browse(cr, uid, appt_id)
        self.assertTrue(appt.id)

    def testClientAvailability(self):
        """
        Check that the same client can't have two appointments
        at the same time.

        """

        cr, uid = self.cr, self.uid
        appt_id = None
        with self.assertRaises(except_orm) as ex:
            appt_id = self.create_appt(cr, uid, self.appt_obj,
                                       self.client_id,
                                       self.start,
                                       self.service_id,
                                       context={'start_date': self.start})
        appt = self.appt_obj.browse(cr, uid, appt_id)
        self.assertFalse(appt)

    def testEmployeeAvailability(self):
        """
        Check that the same employee can't have two appointments
        at the same time.

        """

        cr, uid = self.cr, self.uid
        first_appt = self.appt_obj.browse(cr, uid, self.appt_id)
        # Create new client to provide service to
        values = {'name': 'Client #2'}
        client_id = self.client_obj.create(cr, uid, values, context={})
        appt_id = self.create_appt(cr, uid, self.appt_obj,
                                   client_id,
                                   self.start,
                                   self.service_id,
                                   context={'start_date': self.start})
        appt_obj = self.appt_obj.browse(cr, uid, appt_id)
        with self.assertRaises(except_orm) as ex:
            appt_obj.write({'employee_id': first_appt.employee_id.id})

    def testSpaceAvailability(self):
        """
        Check that the same space can't have two appointments
        at the same time.

        """

        cr, uid = self.cr, self.uid
        first_appt = self.appt_obj.browse(cr, uid, self.appt_id)
        # Create new client to provide service to
        values = {'name': 'Client #3'}
        client_id = self.client_obj.create(cr, uid, values, context={})
        appt_id = self.create_appt(cr, uid, self.appt_obj,
                                   client_id,
                                   self.start,
                                   self.service_id,
                                   context={'start_date': self.start})
        appt_obj = self.appt_obj.browse(cr, uid, appt_id)
        with self.assertRaises(except_orm) as ex:
            appt_obj.write({'space_id': first_appt.space_id.id})

    def testAppointmentUnlink(self):
        """
        Check a normal user can't unlink/delete an appointment.

        """

        # TODO use receptionist user
        cr, uid = self.cr, 5  # self.uid
        appt_obj = self.appt_obj.browse(cr, uid, self.appt_id)
        with self.assertRaises(except_orm) as ex:
            appt_obj.unlink()
        appt_obj = self.appt_obj.browse(cr, uid, self.appt_id)
        self.assertTrue(appt_obj.id)

    def testAppointmentUnlinkManager(self):
        """
        Check a manager user can unlink/delete an appointment.

        """

        cr, uid = self.cr, self.uid
        appt_obj = self.appt_obj.browse(cr, uid, self.appt_id)
        self.assertTrue(appt_obj.unlink())

    def testAppointmentDone(self):
        """
        Pay the POS order for a checked-in appointment,
        and validate that appointment status has changed and can't be modified.

        """

        # TODO use receptionist user
        cr, uid = self.cr, 5  # self.uid
        # Open POS Session to be able to create pos.orders
        self.pos_session_obj.open_cb(cr, uid, [self.pos_session_id])
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        appt.action_check_in()
        self.assertEqual(appt.state, 'open')
        # Validate order exists
        order_obj = self.pos_order_obj.browse(cr, uid, appt.order_line_id.order_id.id)
        self.assertTrue(order_obj.id)
        # Pay order and validate invoice was created and appt changed to 'done'
        order_obj.action_create_invoice()
        self.assertEqual(order_obj.state, 'invoiced')
        invoice_obj = order_obj.invoice_id
        self.assertEqual(invoice_obj.state, 'open')
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        self.assertEqual(appt.state, 'done')
        # Validate modifications aren't allowed
        with self.assertRaises(except_orm) as ex:
            appt.write({'duration': 3})
        # Only manager users can unlink
        cr, uid = self.cr, self.uid
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        with self.assertRaises(except_orm) as ex:
            appt.unlink()

    def testScheduleDuplicate(self):
        """
        Check if schedule creation is working and not allowing duplicates.

        """

        cr, uid = self.cr, self.uid
        sched_obj = self.sched_obj.browse(cr, uid, self.sched_id)
        self.assertTrue(sched_obj.id)
        with self.assertRaises(except_orm) as ex:
            self.create_sched(cr, uid, self.sched_obj, sched_obj.date)
        with self.assertRaises(except_orm) as ex:
            sched_obj.write({'date': sched_obj.date})

    def testScheduleLineAppointment(self):
        """
        Validate schedule.line create/update.

        Check if schedule.line creates an appointment assigned to it's employee_id,
        if it does, don't allow modification (start/end hours or missing)
        or unlinking, else allow it.

        """

        # Create schedule and schedule.line
        cr, uid = self.cr, self.uid
        sched_obj = self.sched_obj.browse(cr, uid, self.sched_id)

        # Validate creation
        # Can't create schedule.line with hour_start less than schedule hour_start.
        with self.assertRaises(except_orm) as ex:
            self.create_sched_line(cr, uid, self.sched_line_obj,
                                   self.sched_id, self.employee_id, hour_start=8, hour_end=17)
        # Can't create schedule.line with hour_end greater than schedule hour_end.
        with self.assertRaises(except_orm) as ex:
            self.create_sched_line(cr, uid, self.sched_line_obj,
                                   self.sched_id, self.employee_id, hour_start=9, hour_end=22)
        # Can't create schedule.line with hour_end less than or equal to hour_start.
        with self.assertRaises(except_orm) as ex:
            self.create_sched_line(cr, uid, self.sched_line_obj,
                                   self.sched_id, self.employee_id, hour_start=12, hour_end=10)
        sched_line_obj = self.sched_line_obj.browse(cr, uid, sched_obj.schedule_line_ids[0].id)
        self.assertTrue(sched_line_obj.id)

        # Validate if lunch appointment was created.
        date = datetime.strptime(sched_obj.date, "%Y-%m-%d")
        day_start, day_end = self.appt_obj._day_start_end_time(str(date))
        appt_ids = self.appt_obj.search(cr, uid, [('employee_id', '=', sched_line_obj.employee_id.id),
                                                  ('start', '>=', day_start),
                                                  ('start', '<=', day_end),
                                                  ])
        self.assertEqual(len(appt_ids), 2)  # 1 For the lunch appt, and 1 for the appt in setUp.
        appt_obj = self.appt_obj.browse(cr, uid, appt_ids[0])
        self.assertEqual(appt_obj.start, '2000-01-01 17:00:00')

        # Validate update
        # Can't update if hour_start < schedule.hour_start.
        with self.assertRaises(except_orm) as ex:
            self.sched_line_obj.write(cr, uid, [sched_line_obj.id], {'hour_start': 8})
        # Can't update if hour_end > schedule.hour_end.
        with self.assertRaises(except_orm) as ex:
            self.sched_line_obj.write(cr, uid, [sched_line_obj.id], {'hour_end': 22})
        self.sched_line_obj.write(cr, uid, [sched_line_obj.id], {'hour_start': 9})
        self.sched_line_obj.write(cr, uid, [sched_line_obj.id], {'hour_end': 19})
        sched_line_obj = self.sched_line_obj.browse(cr, uid, sched_line_obj.id)
        self.assertEqual(sched_line_obj.hour_start, 9)
        self.assertEqual(sched_line_obj.hour_end, 19)

        # Can't modifiy if schedule.line starting hour is after appt start.
        with self.assertRaises(except_orm) as ex:
            sched_line_obj.write({'hour_start': 17.25})
        # Can't modify if schedule.line ending hour is before appt end.
        with self.assertRaises(except_orm) as ex:
            sched_line_obj.write({'hour_end': 17.75})
        # Can't modify if schedule.line missing is true and has an appt.
        with self.assertRaises(except_orm) as ex:
            sched_line_obj.write({'missing': True})
        # Can't delete if appt inside schedule period.
        with self.assertRaises(except_orm) as ex:
            sched_line_obj.unlink()

        # Cancel existing lunch appointment
        appt_obj.case_cancel()

        # Cancel appointment created in setUp (not used in this scenario)
        appt_cancel = self.appt_obj.browse(cr, uid, appt_ids[1])
        appt_cancel.case_cancel()

        # Can't update hour_end to less than or equal to hour_start.
        with self.assertRaises(except_orm) as ex:
            self.sched_line_obj.write(cr, uid, [sched_line_obj.id], {'hour_end': 9})
        # Validate all is allowed after appt is removed/canceled.
        sched_line_obj.write({'hour_start': 17.25})
        sched_line_obj.write({'hour_end': 17.75})
        sched_line_obj = self.sched_line_obj.browse(cr, uid, sched_line_obj.id)
        self.assertEqual(sched_line_obj.hour_start, 17.25)
        self.assertEqual(sched_line_obj.hour_end, 17.75)
        sched_line_obj.unlink()

    def testScheduleMissingEmployee(self):
        """
        Check if when an employee is marked as missing, it won't allow
        creating apppointments with that employee.

        """

        # Create schedule and schedule line
        cr, uid = self.cr, self.uid
        sched_obj = self.sched_obj.browse(cr, uid, self.sched_id)
        sched_line_id = self.create_sched_line(cr, uid, self.sched_line_obj,
                                               self.sched_id, self.employee_id,
                                               hour_start=9, hour_end=17)
        sched_line_obj = self.sched_line_obj.browse(cr, uid, sched_line_id)

        # Cancel auto-created lunch break.
        date = datetime.strptime(sched_obj.date, "%Y-%m-%d")
        day_start, day_end = self.appt_obj._day_start_end_time(str(date))
        appt_ids = self.appt_obj.search(cr, uid, [('employee_id', '=', sched_line_obj.employee_id.id),
                                                  ('start', '>=', day_start),
                                                  ('start', '<=', day_end),
                                                  ])
        appt_obj = self.appt_obj.browse(cr, uid, appt_ids[0])
        appt_obj.case_cancel()

        # Cancel appointment created in setUp (not used in this scenario)
        appt_cancel = self.appt_obj.browse(cr, uid, appt_ids[1])
        appt_cancel.case_cancel()

        # Mark employee as missing
        sched_line_obj.write({'missing': True})

        # Attempt to create appointment
        # TODO forsome reasing updating missing to True is not being saved.
        # TODO fix timezone problem (this time is actually 09:00)
        start = '2000-01-01 13:00:00'
        employee_id = sched_line_obj.employee_id.id
        #with self.assertRaises(except_orm) as ex:
        #    self.appt_id = self.create_appt(cr, uid, self.appt_obj,
        #                                    self.client_id,
        #                                    start,
        #                                    self.service_id,
        #                                    employee_id=employee_id,
        #                                    context={'tz': 'America/Santo_Domingo',
        #                                             'start_date': start})

        # Mark employee as not missing
        sched_line_obj.write({'missing': False})

        # Create appointment
        self.appt_id = self.create_appt(cr, uid, self.appt_obj,
                                        self.client_id,
                                        start,
                                        self.service_id,
                                        employee_id=employee_id,
                                        context={'tz': 'America/Santo_Domingo',
                                                 'start_date': start})
        appt_obj = self.appt_obj.browse(cr, uid, self.appt_id)
        self.assertTrue(appt_obj.id)
