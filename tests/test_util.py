# -*- coding: utf-8 -*-
def create_sched_line(cr, uid, model_obj, sched_id, employee_id, hour_start=9, hour_end=17, context=None):
    """
    Helper to create schedules.

    sched = schedule

    """

    values = {'employee_id': employee_id,
              'hour_start': hour_start,
              'hour_end': hour_end,
              'schedule_id': sched_id}
    return model_obj.create(cr, uid, values)

def create_sched(cr, uid, model_obj, date, hour_start=9, hour_end=21, context=None):
    """
    Helper to create schedules.

    sched = schedule

    """

    values = {'date': date,
              'hour_start': hour_start,
              'hour_end': hour_end
              }
    return model_obj.create(cr, uid, values)

def create_appt(cr, uid, model_obj,
        client_id, start, service_id, employee_id=None, context=None):
    """
    Helper to create appointments.

    appt = appointment

    """

    onchange_values = model_obj.onchange_appointment_service(cr, uid, 0, service_id, employee_id, context=context)['value']
    values = {'client_id': client_id,
              'start': start,
              'service_id': service_id,
              'duration': onchange_values['duration'],
              'price': onchange_values['price'],
              'space_id': onchange_values['space_id'],
              'employee_id': onchange_values['employee_id']
              }
    return model_obj.create(cr, uid, values)
