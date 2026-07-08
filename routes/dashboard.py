from flask import Blueprint, render_template, redirect, session

from models import Business, Appointment, Service, Payment

dashboard = Blueprint("dashboard", __name__)

@dashboard.route("/dashboard")
def dashboard_page():

    print("=== DASHBOARD ROUTE STARTED ===")

    if "business_id" not in session:
        print("No business_id in session")
        return redirect("/login")

    print("business_id:", session["business_id"])

    business_id = session["business_id"]

    business = Business.query.get(business_id)

    print("Business:", business)

    appointments = Appointment.query.filter_by(
        business_id=business_id
    ).all()

    print("Appointments loaded")

    services = Service.query.filter_by(
        business_id=business_id
    ).all()

    print("Services loaded")

    payments = Payment.query.filter_by(
        business_id=business_id
    ).order_by(
        Payment.id.desc()
    ).limit(5).all()

    print("Payments loaded")

    total_revenue = sum(
        a.amount for a in appointments
    )

    customer_count = len(
        set(a.customer_phone for a in appointments)
    )

    print("Rendering dashboard")

    return render_template(
        "dashboard.html",
        business=business,
        appointments=appointments,
        services=services,
        payments=payments,
        revenue=total_revenue,
        customer_count=customer_count
    )
