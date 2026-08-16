from datetime import time
import re


DAY_NAMES = {
    "mon": 0,
    "monday": 0,
    "tue": 1,
    "tues": 1,
    "tuesday": 1,
    "wed": 2,
    "wednesday": 2,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "thursday": 3,
    "fri": 4,
    "friday": 4,
    "sat": 5,
    "saturday": 5,
    "sun": 6,
    "sunday": 6,
}


def parse_time(value, period):
    """Convert 12-hour time into a datetime.time object."""

    hour = int(value)

    if period.lower() == "pm" and hour != 12:
        hour += 12

    if period.lower() == "am" and hour == 12:
        hour = 0

    return hour


def check_business_hours(
    opening_hours,
    appointment_start,
    appointment_end
):
    """
    Check whether an appointment fits within business hours.

    Supported format:

        Mon-Fri 8am-6pm

    Example:

        Monday-Friday 8am-6pm

    Saturday and Sunday are treated as closed unless they
    are explicitly included.
    """

    if not opening_hours:
        return True, ""

    hours_text = opening_hours.strip().lower()

    # -----------------------------------------
    # FIND DAYS
    # -----------------------------------------

    day_match = re.search(
        r"(monday|mon|tuesday|tue|tues|wednesday|wed|"
        r"thursday|thu|thur|thurs|friday|fri|saturday|sat|"
        r"sunday|sun)"
        r"\s*[-–]\s*"
        r"(monday|mon|tuesday|tue|tues|wednesday|wed|"
        r"thursday|thu|thur|thurs|friday|fri|saturday|sat|"
        r"sunday|sun)",
        hours_text
    )

    # -----------------------------------------
    # FIND TIME RANGE
    # -----------------------------------------

    time_match = re.search(
        r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)"
        r"\s*[-–]\s*"
        r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)",
        hours_text
    )

    # If the format isn't recognized, don't
    # accidentally block bookings.
    if not time_match:
        return True, ""

    # -----------------------------------------
    # DETERMINE OPEN DAYS
    # -----------------------------------------

    if day_match:

        start_day = DAY_NAMES[
            day_match.group(1)
        ]

        end_day = DAY_NAMES[
            day_match.group(2)
        ]

        if start_day <= end_day:

            open_days = set(
                range(
                    start_day,
                    end_day + 1
                )
            )

        else:

            # Handles ranges such as Fri-Mon
            open_days = set(
                list(range(start_day, 7))
                + list(range(0, end_day + 1))
            )

    else:
        # If no days are specified, assume every day.
        open_days = set(range(7))

    # -----------------------------------------
    # CHECK APPOINTMENT DAY
    # -----------------------------------------

    appointment_day = appointment_start.weekday()

    if appointment_day not in open_days:

        return (
            False,
            "Sorry, we are closed on that day. "
            "Please choose another date."
        )

    # -----------------------------------------
    # CONVERT TIMES
    # -----------------------------------------

    start_hour = parse_time(
        time_match.group(1),
        time_match.group(3)
    )

    start_minute = int(
        time_match.group(2) or 0
    )

    end_hour = parse_time(
        time_match.group(4),
        time_match.group(6)
    )

    end_minute = int(
        time_match.group(5) or 0
    )

    business_start = time(
        start_hour,
        start_minute
    )

    business_end = time(
        end_hour,
        end_minute
    )

    # -----------------------------------------
    # CHECK APPOINTMENT START
    # -----------------------------------------

    if appointment_start.time() < business_start:

        return (
            False,
            "Sorry, that appointment starts before "
            "our opening time. Please choose a later time."
        )

    # -----------------------------------------
    # CHECK APPOINTMENT END
    # -----------------------------------------

    if appointment_end.time() > business_end:

        return (
            False,
            "Sorry, that appointment would finish "
            "after our closing time. Please choose "
            "an earlier time."
        )

    return True, ""