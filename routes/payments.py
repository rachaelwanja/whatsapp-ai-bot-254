from flask import (
    Blueprint,
    render_template,
    redirect,
    session
)

from models import Payment

payments = Blueprint(
    "payments",
    __name__
)

# =========================================
# PAYMENTS
# =========================================

@payments.route("/payments")
def payments_page():

    if "business_id" not in session:
        return redirect("/login")

    payments = Payment.query.order_by(
        Payment.id.desc()
    ).all()

    return render_template(
        "payments.html",
        payments=payments
    )
