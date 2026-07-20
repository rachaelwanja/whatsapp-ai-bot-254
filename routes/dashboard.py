from flask import (
    Blueprint,
    render_template,
    redirect,
    session,
    request,
    flash
)

from models import (
    db,
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
    
# =========================================
# BUSINESS SETTINGS
# =========================================

@dashboard.route("/business-settings", methods=["GET", "POST"])
def business_settings():

    if "business_id" not in session:
        return redirect("/login")

    business = Business.query.get(
        session["business_id"]
    )

    if request.method == "POST":

        business.business_name = request.form.get(
            "business_name"
        )

        business.business_type = request.form.get(
            "business_type"
        )

        business.business_phone = request.form.get(
            "business_phone"
        )

        business.location = request.form.get(
            "location"
        )

        business.opening_hours = request.form.get(
            "opening_hours"
        )

        business.ai_prompt = request.form.get(
            "ai_prompt"
        )

        db.session.commit()

        flash("Business settings saved!")

        return redirect("/business-settings")

    return render_template(
        "business_settings.html",
        business=business
    )
    
# =========================================
# AI EMPLOYEE
# =========================================

@dashboard.route("/ai-employee")
def ai_employee():

    if "business_id" not in session:
        return redirect("/login")

    business = Business.query.get(
        session["business_id"]
    )

    return render_template(
        "ai_employee.html",
        business=business
    )
