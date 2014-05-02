# -*- coding: utf-8 -*-
from openerp.tests import common
from openerp.osv.orm import except_orm

class TestSchedule(common.TransactionCase):
    def create_sched(self, cr, uid, model_obj, date, context=None):
        """
        Helper to create schedules.

        """

        values = {'date': date, 'hour_start': 9, 'hour_end': 21}
        return model_obj.create(cr, uid, values)

    # Refator this methos to avoid repetition (it also exists in test_salon_spa.py)
    def create_appt(self, cr, uid, model_obj,
            client_id, start, service_id, employee_id=None, context=None):
        """
        Helper to create appointments.

        appt = appointment

        """

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
                  'space_id': onchange_values['space_id'],
                  'employee_id': onchange_values['employee_id']
                  }
        return model_obj.create(cr, uid, values)

    def setUp(self):
        super(TestSchedule, self).setUp()

        # Cursor and user initialization
        cr, uid = self.cr, self.uid

        # Modules to test
        self.sched_obj = self.registry('salon.spa.schedule')
        self.sched_line_obj = self.registry('salon.spa.schedule.line')
        # appt = appointment
        self.appt_obj = self.registry('salon.spa.appointment')

        date = '2000-05-01'
        self.sched_id = self.create_sched(cr, uid, self.sched_obj, date)

        # Negative tests data

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

        Check if schedule.line has an appointment assigned to it's employee_id,
        if it does, don't allow modification (start/end hours or missing)
        or unlinking, else allow it.
        
        """

        # Create schedule and schedule line
        cr, uid = self.cr, self.uid
        sched_obj = self.sched_obj.browse(cr, uid, self.sched_id)

        # Validate creation
        values = {'employee_id': 25, 'hour_start': 8, 'hour_end': 17, 'schedule_id': sched_obj.id}
        with self.assertRaises(except_orm) as ex:
            self.sched_line_obj.create(cr, uid, values)
        values = {'employee_id': 25, 'hour_start': 9, 'hour_end': 22, 'schedule_id': sched_obj.id}
        with self.assertRaises(except_orm) as ex:
            self.sched_line_obj.create(cr, uid, values)
        values = {'employee_id': 25, 'hour_start': 9, 'hour_end': 17, 'schedule_id': sched_obj.id}
        sched_line_id = self.sched_line_obj.create(cr, uid, values)
        sched_line_obj = self.sched_line_obj.browse(cr, uid, sched_line_id)
        self.assertTrue(sched_line_obj.id)

        # Validate update 
        values = {'hour_start': 8}
        with self.assertRaises(except_orm) as ex:
            self.sched_line_obj.write(cr, uid, [sched_line_obj.id], values)
        values = {'hour_end': 22}
        with self.assertRaises(except_orm) as ex:
            self.sched_line_obj.write(cr, uid, [sched_line_obj.id], values)
        values = {'hour_end': 9}
        self.sched_line_obj.write(cr, uid, [sched_line_obj.id], values)
        values = {'hour_end': 17}
        self.sched_line_obj.write(cr, uid, [sched_line_obj.id], values)
        sched_line_obj = self.sched_line_obj.browse(cr, uid, sched_line_id)
        self.assertTrue(sched_line_obj.hour_start == 9)
        self.assertTrue(sched_line_obj.hour_end == 17)

        # Create appointment
        client_id = 68
        start = '2014-05-01 12:30:00'
        service_id =  25
        employee_id = sched_line_obj.employee_id.id
        self.appt_id = self.create_appt(cr, uid, self.appt_obj,
                                        client_id,
                                        start,
                                        service_id,
                                        employee_id=employee_id,
                                        context={'start_date': start})
        appt_obj = self.appt_obj.browse(cr, uid, self.appt_id)

        # Can't modifiy if new schedule.line starting hour is after appt start.
        with self.assertRaises(except_orm) as ex:
            sched_line_obj.write({'hour_start': 12.51})
        # Can't modify if new schedule.line ending hour is before appt end.
        with self.assertRaises(except_orm) as ex:
            sched_line_obj.write({'hour_end': 13.49})
        # Can't delete if appt inside schedule period.
        with self.assertRaises(except_orm) as ex:
            sched_line_obj.unlink()

        # Validate all is allowed after appt is removed.
        appt_obj.unlink()
        sched_line_obj.write({'hour_start': 12.51})
        sched_line_obj.write({'hour_end': 13.49})
        sched_line_obj.unlink()
        sched_line_obj = self.sched_obj.browse(cr, uid, sched_line_id)
        self.assertFalse(sched_line_obj.id)
