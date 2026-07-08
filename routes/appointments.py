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

# =========================================
# ADD APPOINTMENT
# =========================================

@appointments.route("/add-appointment", methods=["POST"])
def add_appointment():

    if "business_id" not in session:
        return redirect("/login")

    business_id = session["business_id"]

    appointment_time = request.form.get(
        "appointment_time"
    )

    existing = Appointment.query.filter_by(

        business_id=business_id,

        appointment_time=appointment_time

    ).first()

    if existing:

        flash(
            "Time slot already booked"
        )

        return redirect(
            "/dashboard"
        )

    appointment = Appointment(

        business_id=business_id,

        customer_name=request.form.get(
            "customer_name"
        ),

        customer_phone=request.form.get(
            "customer_phone"
        ),

        service=request.form.get(
            "service"
        ),

        amount=int(
            request.form.get("amount")
        ),

        appointment_time=appointment_time

    )

    db.session.add(
        appointment
    )

    db.session.commit()

    flash("Appointment added successfully!")

    return redirect(
        "/dashboard"
    )

