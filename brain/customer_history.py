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


def format_customer_history(
    appointments,
    customer_name=""
):
    """
    Convert appointment history into a short
    text block that can be included in the AI prompt.
    """

    if not appointments:
        return ""

    lines = [
        "CUSTOMER HISTORY"
    ]

    if customer_name:
        lines.append(
            f"Customer: {customer_name}"
        )

    lines.append(
        "Recent appointments:"
    )

    for appointment in appointments:

        appointment_time = appointment.appointment_time

        if appointment_time:

            if isinstance(appointment_time, str):

                formatted_time = appointment_time

            else:

                formatted_time = appointment_time.strftime(
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

        lines.append(
            f"- {service} — "
            f"{formatted_time} — "
            f"{status}"
        )

    return "\n".join(lines)
