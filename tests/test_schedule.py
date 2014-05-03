# -*- coding: utf-8 -*-
from openerp.tests import common
from openerp.osv.orm import except_orm

from datetime import datetime


class TestSchedule(common.TransactionCase):
    # TODO REFACTOR, this is a duplicate method
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

        date = '2000-01-01'
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

        Check if schedule.line creates an appointment assigned to it's employee_id,
        if it does, don't allow modification (start/end hours or missing)
        or unlinking, else allow it.
        
        """

        # Create schedule and schedule line
        cr, uid = self.cr, self.uid
        sched_obj = self.sched_obj.browse(cr, uid, self.sched_id)

        # Validate creation
        # Can't create schedule.line with hour_start less than schedule hour_start.
        values = {'employee_id': 25, 'hour_start': 8, 'hour_end': 17, 'schedule_id': sched_obj.id}
        with self.assertRaises(except_orm) as ex:
            self.sched_line_obj.create(cr, uid, values)
        # Can't create schedule.line with hour_end greater than schedule hour_end.
        values = {'employee_id': 25, 'hour_start': 9, 'hour_end': 22, 'schedule_id': sched_obj.id}
        with self.assertRaises(except_orm) as ex:
            self.sched_line_obj.create(cr, uid, values)
        # Can't create schedule.line with hour_end less than or equal to hour_start.
        values = {'employee_id': 25, 'hour_start': 12, 'hour_end': 10, 'schedule_id': sched_obj.id}
        with self.assertRaises(except_orm) as ex:
            self.sched_line_obj.create(cr, uid, values)
        values = {'employee_id': 25, 'hour_start': 9, 'hour_end': 17, 'schedule_id': sched_obj.id}
        sched_line_id = self.sched_line_obj.create(cr, uid, values)
        sched_line_obj = self.sched_line_obj.browse(cr, uid, sched_line_id)
        self.assertTrue(sched_line_obj.id)

        # Validate if lunch appointment was created.
        date = datetime.strptime(sched_obj.date, "%Y-%m-%d")
        day_start, day_end = self._day_start_end_time(str(date))
        appt_ids = self.appt_obj.search(cr, uid, [('employee_id', '=', sched_line_obj.employee_id.id),
                                                  ('start', '>=', day_start),
                                                  ('start', '<=', day_end),
                                                  ])
        appt_obj = self.appt_obj.browse(cr, uid, appt_ids[0])
        self.assertEqual(appt_obj.start, '2000-01-01 17:00:00')

        # Validate update 
        # Can't update if hour_start < schedule.hour_start.
        values = {'hour_start': 8}
        with self.assertRaises(except_orm) as ex:
            self.sched_line_obj.write(cr, uid, [sched_line_obj.id], values)
        # Can't update if hour_end > schedule.hour_end.
        values = {'hour_end': 22}
        with self.assertRaises(except_orm) as ex:
            self.sched_line_obj.write(cr, uid, [sched_line_obj.id], values)
        values = {'hour_start': 9}
        self.sched_line_obj.write(cr, uid, [sched_line_obj.id], values)
        values = {'hour_end': 19}
        self.sched_line_obj.write(cr, uid, [sched_line_obj.id], values)
        sched_line_obj = self.sched_line_obj.browse(cr, uid, sched_line_id)
        self.assertTrue(sched_line_obj.hour_start == 9)
        self.assertTrue(sched_line_obj.hour_end == 19)


        # Can't modifiy if schedule.line starting hour is after appt start.
        with self.assertRaises(except_orm) as ex:
            sched_line_obj.write({'hour_start': 17.25})
        # Can't modify if schedule.line ending hour is before appt end.
        with self.assertRaises(except_orm) as ex:
            sched_line_obj.write({'hour_end': 17.50})
        # Can't modify if schedule.line missing is true and has an appt.
        with self.assertRaises(except_orm) as ex:
            sched_line_obj.write({'missing': True})
        # Can't delete if appt inside schedule period.
        with self.assertRaises(except_orm) as ex:
            sched_line_obj.unlink()

        # Cancel existing appointment
        appt_obj.case_cancel()

        # Can't update hour_end to less than or equal to hour_start.
        values = {'hour_end': 9}
        with self.assertRaises(except_orm) as ex:
            self.sched_line_obj.write(cr, uid, [sched_line_obj.id], values)
        # Validate all is allowed after appt is removed/canceled.
        sched_line_obj.write({'hour_start': 17.25})
        sched_line_obj.write({'hour_end': 17.50})
        sched_line_obj = self.sched_line_obj.browse(cr, uid, sched_line_id)
        self.assertTrue(sched_line_obj.hour_start == 17.25)
        self.assertTrue(sched_line_obj.hour_end == 17.50)
        sched_line_obj.unlink()
