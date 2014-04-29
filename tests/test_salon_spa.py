# -*- coding: utf-8 -*-
from openerp.tests import common
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
        self.pos_order_obj = self.registry('pos.order')

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
                                   context={'start_date': appt_cancel.start})
        appt = self.appt_obj.browse(cr, uid, appt_id)
        self.assertTrue(appt.id)

    def testClientAvailability(self):
        """
        Check that the same client can't have two appointments
        at the same time.
        
        """

        cr, uid = self.cr, self.uid
        first_appt = self.appt_obj.browse(cr, uid, self.appt_id)
        start = '2014-04-25 16:30:00'
        service_id =  25
        appt_id = None
        with self.assertRaises(except_orm) as ex:
            appt_id = self.create_appt(cr, uid, self.appt_obj,
                                       first_appt.client_id.id,
                                       start,
                                       service_id,
                                       context={'start_date': start})
        appt = self.appt_obj.browse(cr, uid, appt_id)
        self.assertTrue(ex.exception.name == 'Error')
        self.assertFalse(appt)

    def testEmployeeAvailability(self):
        """
        Check that the same employee can't have two appointments
        at the same time.
        
        """

        cr, uid = self.cr, self.uid
        first_appt = self.appt_obj.browse(cr, uid, self.appt_id)
        client_id = 33
        start = '2014-04-25 16:30:00'
        service_id =  25
        appt_id = self.create_appt(cr, uid, self.appt_obj,
                                   client_id,
                                   start,
                                   service_id,
                                   context={'start_date': start})
        appt = self.appt_obj.browse(cr, uid, appt_id)
        with self.assertRaises(except_orm) as ex:
            appt.write({'employee_id': first_appt.employee_id.id})
        self.assertTrue(ex.exception.name == 'Error')
        self.assertTrue(appt.employee_id.id == first_appt.employee_id.id)

    def testSpaceAvailability(self):
        """
        Check that the same space can't have two appointments
        at the same time.
        
        """

        cr, uid = self.cr, self.uid
        first_appt = self.appt_obj.browse(cr, uid, self.appt_id)
        client_id = 33
        start = '2014-04-25 16:30:00'
        service_id =  25
        appt_id = self.create_appt(cr, uid, self.appt_obj,
                                   client_id,
                                   start,
                                   service_id,
                                   context={'start_date': start})
        appt = self.appt_obj.browse(cr, uid, appt_id)
        with self.assertRaises(except_orm) as ex:
            appt.write({'space_id': first_appt.space_id.id})
        self.assertTrue(ex.exception.name == 'Error')
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
        self.assertTrue(ex.exception.name)
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
