# -*- coding: utf-8 -*-
from openerp.tests import common
from openerp.tools.translate import _
from openerp.osv.orm import except_orm


class TestSalonSpa(common.TransactionCase):
    def create_appt(self, cr, uid, model_obj,
            client_id, start, service_id, context=None):
        """
        Helper to create appointments.

        appt = appointment

        """

        # TODO get real id sequence
        ids = self.appt_obj.search(cr, uid, [],
                order='create_date desc', context=context)
        ids = ids[0] + 1
        onchange_values = model_obj.onchange_appointment_service(cr, uid, ids, service_id, context=context)['value']
        values = {'client_id': client_id,
                  'start': start,
                  'service_id': service_id,
                  'duration': onchange_values['duration'],
                  'price': onchange_values['price'],
                  'space_id': onchange_values['space_id'],
                  'category_id': onchange_values['category_id'],
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

        # Positive tests data
        client_id = 68
        start = '2014-04-25 16:30:00'
        service_id =  25
        self.appt_id = self.create_appt(cr, uid, self.appt_obj,
                                        client_id,
                                        start,
                                        service_id,
                                        context={'start_date': start})

        # Negative tests data

    def testAppointmentCreated(self):
        """
        Check if appontment creation is working.
        
        """

        cr, uid = self.cr, self.uid
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        self.assertTrue(appt.id)

    def testAppointmentCancel(self):
        """
        Check canceling appointment changes it to proper status.
        
        """

        cr, uid = self.cr, self.uid
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        appt.action_cancel()
        self.assertTrue(appt.state == 'cancel')

    def testAppointmentUnlink(self):
        """
        Check a normal user can't unlink/delete an appointment.
        
        """

        # TODO use receptionist user
        cr, uid = self.cr, 5  # self.uid
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        
        with self.assertRaises(except_orm) as ex:
            appt.unlink()
        exception = ex.exception
        self.assertTrue(exception.name)
        self.assertTrue(appt.id)

    def testAppointmentUnlinkManager(self):
        """
        Check a manager user can unlink/delete an appointment.
        
        """

        cr, uid = self.cr, self.uid
        appt = self.appt_obj.browse(cr, uid, self.appt_id)
        self.assertTrue(appt.unlink())
