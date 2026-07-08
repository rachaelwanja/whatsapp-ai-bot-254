from flask import (
    Blueprint,
    render_template,
    redirect,
    session
)

from models import (
    Business,
    Service
)

services = Blueprint(
    "services",
    __name__
)

# =========================================
# SERVICES
# =========================================

@services.route("/services")
def services_page():

    if "business_id" not in session:
        return redirect("/login")

    business_id = session["business_id"]

    business = Business.query.get(
        business_id
    )

    all_services = Service.query.filter_by(
        business_id=business_id
    ).all()

    return render_template(
        "services.html",
        business=business,
        services=all_services
    )
