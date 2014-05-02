# -*- coding: utf-8 -*-
from openerp.tests import common
from openerp.osv.orm import except_orm


class TestSalonSpa(common.TransactionCase):
    def create_sched(self, cr, uid, model_obj, date, context=None):
        """
        Helper to create schedules.

        """

        values = {'date': date, 'hour_start': 9, 'hour_end': 21}
        return model_obj.create(cr, uid, values)

    def setUp(self):
        super(TestSalonSpa, self).setUp()

        # Cursor and user initialization
        cr, uid = self.cr, self.uid

        # Modules to test
        self.sched_obj = self.registry('salon.spa.schedule')
        self.sched_line_obj = self.registry('salon.spa.schedule.line')

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

    def testScheduleLineCreation(self):
        """
        Check if schedule.line creation is working.
        
        """

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
