from flask import (
    Blueprint,
    render_template,
    redirect,
    session
)

from models import (
    Appointment
)

customers = Blueprint(
    "customers",
    __name__
)

# =========================================
# CUSTOMERS
# =========================================

@customers.route("/customers")
def customers_page():

    if "business_id" not in session:

        return redirect("/login")

    customers = Appointment.query.filter_by(
        business_id=session["business_id"]
    ).all()

    return render_template(
        "customers.html",
        customers=customers
    )
