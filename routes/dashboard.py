from flask import Blueprint, render_template, redirect, session

from models import (
    Business,
    Appointment,
    Service,
    Payment
)

# =========================================
# BLUEPRINT
# =========================================

dashboard = Blueprint(
    "dashboard",
    __name__
)

# =========================================
# DASHBOARD
# =========================================

@dashboard.route("/dashboard")
def dashboard_page():

    if "business_id" not in session:
        return redirect("/login")

    business_id = session["business_id"]

    business = Business.query.get(
        business_id
    )

    appointments = Appointment.query.filter_by(
        business_id=business_id
    ).all()

    services = Service.query.filter_by(
        business_id=business_id
    ).all()

    payments = Payment.query.filter_by(
        business_id=business_id
    ).order_by(
        Payment.id.desc()
    ).limit(5).all()

    total_revenue = sum(
        appointment.amount
        for appointment in appointments
    )

    customer_count = len(
        set(
            appointment.customer_phone
            for appointment in appointments
        )
    )

    return render_template(
        "dashboard.html",
        business=business,
        appointments=appointments,
        services=services,
        payments=payments,
        revenue=total_revenue,
        customer_count=customer_count
    )
