from datetime import datetime

from models import Appointment


def get_customer_history(
    business_id,
    customer_phone,
    limit=5
):
    """
    Get the customer's most recent appointments.
    """

    appointments = Appointment.query.filter_by(
        business_id=business_id,
        customer_phone=customer_phone
    ).order_by(
        Appointment.appointment_time.desc()
    ).limit(
        limit
    ).all()

    return appointments


def get_appointment_datetime(appointment):
    """
    Return appointment time as a Python datetime.
    """

    appointment_time = appointment.appointment_time

    if not appointment_time:
        return None

    if isinstance(appointment_time, datetime):
        return appointment_time

    if isinstance(appointment_time, str):

        try:
            return datetime.fromisoformat(
                appointment_time
            )
        except ValueError:
            return None

    return None


def split_customer_history(appointments):
    """
    Separate appointments into past and upcoming.
    """

    now = datetime.now()

    past_appointments = []
    upcoming_appointments = []

    for appointment in appointments:

        appointment_datetime = get_appointment_datetime(
            appointment
        )

        if not appointment_datetime:
            continue

        if appointment_datetime < now:
            past_appointments.append(
                appointment
            )
        else:
            upcoming_appointments.append(
                appointment
            )

    past_appointments.sort(
        key=get_appointment_datetime,
        reverse=True
    )

    upcoming_appointments.sort(
        key=get_appointment_datetime
    )

    return (
        past_appointments,
        upcoming_appointments
    )


def format_appointment(appointment):
    """
    Format a single appointment.
    """

    appointment_datetime = get_appointment_datetime(
        appointment
    )

    if appointment_datetime:

        formatted_time = appointment_datetime.strftime(
            "%B %d, %Y at %I:%M %p"
        )

        formatted_time = (
            formatted_time
            .replace(" 0", " ")
            .replace(" at 0", " at ")
        )

    else:

        formatted_time = "Unknown time"

    service = (
        appointment.service
        or "Unknown service"
    )

    status = (
        appointment.status
        or "Unknown status"
    )

    return (
        f"- {service} — "
        f"{formatted_time} — "
        f"{status}"
    )


def format_customer_history(
    appointments,
    customer_name=""
):
    """
    Format appointment history for the AI.
    """

    if not appointments:
        return ""

    past_appointments, upcoming_appointments = (
        split_customer_history(
            appointments
        )
    )

    lines = [
        "CUSTOMER HISTORY"
    ]

    if customer_name:
        lines.append(
            f"Customer: {customer_name}"
        )

    # -------------------------------
    # LAST COMPLETED APPOINTMENT
    # -------------------------------

    if past_appointments:

        lines.append(
            "LAST COMPLETED APPOINTMENT:"
        )

        lines.append(
            format_appointment(
                past_appointments[0]
            )
        )

    else:

        lines.append(
            "LAST COMPLETED APPOINTMENT: None"
        )

    # -------------------------------
    # NEXT UPCOMING APPOINTMENT
    # -------------------------------

    if upcoming_appointments:

        lines.append(
            "NEXT UPCOMING APPOINTMENT:"
        )

        lines.append(
            format_appointment(
                upcoming_appointments[0]
            )
        )

    else:

        lines.append(
            "NEXT UPCOMING APPOINTMENT: None"
        )

    # -------------------------------
    # FULL HISTORY
    # -------------------------------

    if past_appointments:

        lines.append(
            "PAST APPOINTMENTS:"
        )

        for appointment in past_appointments:

            lines.append(
                format_appointment(
                    appointment
                )
            )

    else:

        lines.append(
            "PAST APPOINTMENTS: None"
        )

    if upcoming_appointments:

        lines.append(
            "UPCOMING APPOINTMENTS:"
        )

        for appointment in upcoming_appointments:

            lines.append(
                format_appointment(
                    appointment
                )
            )

    else:

        lines.append(
            "UPCOMING APPOINTMENTS: None"
        )

    return "\n".join(lines)
