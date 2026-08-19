import json
import re
from datetime import datetime, timedelta

from models import db, Appointment, Service
from brain.business_hours import check_business_hours


def process_reschedule(
    reply,
    business,
    customer_phone
):
    """
    Process a confirmed [RESCHEDULE_REQUEST].

    The database is the source of truth for the
    customer's existing appointment.

    A failed reschedule attempt NEVER changes the
    existing appointment.
    """

    try:

        # =====================================
        # EXTRACT JSON FROM AI RESPONSE
        # =====================================

        reschedule_json = reply.split(
            "[RESCHEDULE_REQUEST]",
            1
        )[1].strip()

        reschedule_data = json.loads(
            reschedule_json
        )

        old_date = reschedule_data.get("old_date")
        old_time = reschedule_data.get("old_time")
        new_date = reschedule_data.get("new_date")
        new_time = reschedule_data.get("new_time")

        print(
            "========== RESCHEDULE DATA =========="
        )

        print("AI OLD DATE:", old_date)
        print("AI OLD TIME:", old_time)
        print("AI NEW DATE:", new_date)
        print("AI NEW TIME:", new_time)

        # =====================================
        # VALIDATE NEW DATE/TIME
        # =====================================

        if not new_date:
            raise ValueError("Missing new_date")

        if not new_time:
            raise ValueError("Missing new_time")

        new_start = datetime.strptime(
            f"{new_date} {new_time}",
            "%Y-%m-%d %H:%M"
        )

        # =====================================
        # FIND CUSTOMER'S REAL APPOINTMENT
        # =====================================

        appointment = None

        # First try the exact old date/time
        # provided by the AI.

        if (
            old_date
            and old_time
            and old_time != "HH:MM"
        ):

            try:

                old_datetime = datetime.strptime(
                    f"{old_date} {old_time}",
                    "%Y-%m-%d %H:%M"
                )

                appointment = (
                    Appointment.query.filter_by(
                        business_id=business.id,
                        customer_phone=customer_phone,
                        appointment_time=(
                            old_datetime.strftime(
                                "%Y-%m-%d %H:%M"
                            )
                        ),
                        status="confirmed"
                    ).first()
                )

            except (
                ValueError,
                TypeError
            ):

                appointment = None

        # =====================================
        # FALLBACK TO DATABASE
        # =====================================
        #
        # If the AI gives us the wrong old time,
        # find the customer's confirmed appointment
        # directly from the database.
        #
        # This is what protects us when a previous
        # reschedule attempt failed.
        # =====================================

        if not appointment:

            confirmed_appointments = (
                Appointment.query.filter_by(
                    business_id=business.id,
                    customer_phone=customer_phone,
                    status="confirmed"
                )
                .order_by(
                    Appointment.appointment_time.asc()
                )
                .all()
            )

            if len(confirmed_appointments) == 1:

                appointment = (
                    confirmed_appointments[0]
                )

            elif len(confirmed_appointments) > 1:

                # If there are multiple appointments,
                # require the AI's old date/time to identify
                # the correct one.

                if old_date:

                    date_matches = []

                    for existing in confirmed_appointments:

                        try:

                            existing_datetime = (
                                datetime.strptime(
                                    existing.appointment_time,
                                    "%Y-%m-%d %H:%M"
                                )
                            )

                        except (
                            ValueError,
                            TypeError
                        ):

                            continue

                        if (
                            existing_datetime.strftime(
                                "%Y-%m-%d"
                            )
                            == old_date
                        ):

                            date_matches.append(
                                existing
                            )

                    if len(date_matches) == 1:

                        appointment = (
                            date_matches[0]
                        )

                    elif len(date_matches) > 1:

                        return (
                            "I found more than one confirmed "
                            "appointment on that date. "
                            "Please provide the time of the "
                            "appointment you want to reschedule."
                        )

        # =====================================
        # NO APPOINTMENT FOUND
        # =====================================

        if not appointment:

            return (
                "I couldn't find a confirmed appointment "
                "for you. Please check the appointment "
                "details and try again."
            )

        # =====================================
        # DATABASE IS SOURCE OF TRUTH
        # =====================================

        old_appointment_time = (
            appointment.appointment_time
        )

        print(
            "========== EXISTING APPOINTMENT =========="
        )

        print(
            "APPOINTMENT ID:",
            appointment.id
        )

        print(
            "CURRENT APPOINTMENT:",
            old_appointment_time
        )

        print(
            "REQUESTED NEW TIME:",
            new_start.strftime(
                "%Y-%m-%d %H:%M"
            )
        )

        # =====================================
        # FIND SERVICE
        # =====================================

        service = Service.query.filter_by(
            business_id=business.id,
            name=appointment.service
        ).first()

        if service:

            duration_match = re.search(
                r"\d+",
                str(
                    service.duration
                ).lower()
            )

            duration_hours = (
                int(
                    duration_match.group()
                )
                if duration_match
                else 1
            )

        else:

            duration_hours = 1

        # =====================================
        # CALCULATE NEW END TIME
        # =====================================

        new_end = (
            new_start
            + timedelta(
                hours=duration_hours
            )
        )

        # =====================================
        # CHECK BUSINESS HOURS
        # =====================================

        within_hours, hours_error = (
            check_business_hours(
                business.opening_hours,
                new_start,
                new_end
            )
        )

        if not within_hours:

            return hours_error

        # =====================================
        # CHECK DOUBLE BOOKING
        # =====================================

        existing_appointments = (
            Appointment.query.filter_by(
                business_id=business.id,
                status="confirmed"
            ).all()
        )

        for existing in existing_appointments:

            # Ignore the appointment being moved.

            if existing.id == appointment.id:
                continue

            try:

                existing_start = (
                    datetime.strptime(
                        existing.appointment_time,
                        "%Y-%m-%d %H:%M"
                    )
                )

            except (
                ValueError,
                TypeError
            ):

                continue

            # ---------------------------------
            # FIND EXISTING SERVICE
            # ---------------------------------

            existing_service = (
                Service.query.filter_by(
                    business_id=business.id,
                    name=existing.service
                ).first()
            )

            if existing_service:

                existing_duration_match = (
                    re.search(
                        r"\d+",
                        str(
                            existing_service.duration
                        ).lower()
                    )
                )

                existing_duration_hours = (
                    int(
                        existing_duration_match.group()
                    )
                    if existing_duration_match
                    else 1
                )

            else:

                existing_duration_hours = 1

            existing_end = (
                existing_start
                + timedelta(
                    hours=existing_duration_hours
                )
            )

            # ---------------------------------
            # OVERLAP
            # ---------------------------------

            if (
                new_start < existing_end
                and new_end > existing_start
            ):

                print(
                    "========== RESCHEDULE CONFLICT =========="
                )

                return (
                    f"Sorry, {new_date} at {new_time} "
                    "is already booked. Please choose "
                    "another time."
                )

        # =====================================
        # UPDATE DATABASE
        # =====================================

        appointment.appointment_time = (
            new_start.strftime(
                "%Y-%m-%d %H:%M"
            )
        )

        db.session.commit()

        # =====================================
        # SUCCESS
        # =====================================

        print(
            "========== APPOINTMENT RESCHEDULED =========="
        )

        print(
            "APPOINTMENT ID:",
            appointment.id
        )

        print(
            "OLD TIME:",
            old_appointment_time
        )

        print(
            "NEW TIME:",
            new_start.strftime(
                "%Y-%m-%d %H:%M"
            )
        )

        return (
            f"Your appointment for "
            f"{appointment.service} has been "
            f"rescheduled successfully from "
            f"{old_appointment_time} to "
            f"{new_date} at {new_time}."
        )

    # =====================================
    # JSON ERROR
    # =====================================

    except json.JSONDecodeError as e:

        print(
            "RESCHEDULE JSON ERROR:",
            e
        )

        db.session.rollback()

        return (
            "Sorry, I couldn't understand the "
            "rescheduling details. Please try again."
        )

    # =====================================
    # DATA ERROR
    # =====================================

    except (
        ValueError,
        KeyError,
        TypeError
    ) as e:

        print(
            "RESCHEDULE DATA ERROR:",
            e
        )

        db.session.rollback()

        return (
            "Sorry, I couldn't process the "
            "rescheduling details. Please check "
            "the appointment information and try again."
        )

    # =====================================
    # GENERAL ERROR
    # =====================================

    except Exception as e:

        print(
            "RESCHEDULE ERROR:",
            e
        )

        db.session.rollback()

        return (
            "Sorry, I couldn't process the "
            "rescheduling. Please check the "
            "appointment details and try again."
        )