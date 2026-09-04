from flask import Blueprint, render_template

from models import Business, Service


catalog = Blueprint(
    "catalog",
    __name__
)


# =========================================
# PUBLIC BUSINESS CATALOG
# =========================================

@catalog.route("/catalog/<int:business_id>")
def business_catalog(business_id):

    # -----------------------------------------
    # FIND BUSINESS
    # -----------------------------------------

    business = Business.query.get_or_404(
        business_id
    )

    # -----------------------------------------
    # GET AVAILABLE SERVICES
    # -----------------------------------------

    services = Service.query.filter_by(
        business_id=business_id,
        available=True
    ).order_by(
        Service.created_at.desc()
    ).all()

    # -----------------------------------------
    # SHOW CATALOG
    # -----------------------------------------

    return render_template(
        "catalog.html",
        business=business,
        services=services
    )