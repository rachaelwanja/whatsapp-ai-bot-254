from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    flash
)

from models import (
    db,
    Business,
    Appointment
)

appointments = Blueprint(
    "appointments",
    __name__
)

# =========================================
# APPOINTMENTS
# =========================================

@appointments.route("/appointments")
def appointments_page():

    if "business_id" not in session:
        return redirect("/login")

    business_id = session["business_id"]

    business = Business.query.get(
        business_id
    )

    appointments = Appointment.query.filter_by(
        business_id=business_id
    ).order_by(
        Appointment.created_at.desc()
    ).all()

    return render_template(
        "appointments.html",
        business=business,
        appointments=appointments
    )
