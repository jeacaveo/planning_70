# -*- coding: utf-8 -*-
from openerp.tests import common
from openerp.osv.orm import except_orm


class TestSalonSpa(common.TransactionCase):
    def create_sched(self, cr, uid, model_obj, date, context=None):
        """
        Helper to create schedules.

        """

        values = {'date': date}
        return model_obj.create(cr, uid, values)

    def setUp(self):
        super(TestSalonSpa, self).setUp()

        # Cursor and user initialization
        cr, uid = self.cr, self.uid

        # Modules to test
        self.sched_obj = self.registry('salon.spa.schedule')

        date = '2014-05-01'
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
