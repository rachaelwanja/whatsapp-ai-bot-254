from models import Appointment


def get_customer_history(
    business_id,
    customer_phone
):

    appointments = Appointment.query.filter_by(
        business_id=business_id,
        customer_phone=customer_phone
    ).order_by(
        Appointment.appointment_time.desc()
    ).all()

    return appointments