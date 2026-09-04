# =========================================
# CUSTOMERS ROUTES
# =========================================

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    flash
)

from models import db, Customer


# =========================================
# BLUEPRINT
# =========================================

customers = Blueprint(
    "customers",
    __name__
)


# =========================================
# CUSTOMER LIST
# =========================================

@customers.route("/customers")
def customer_list():

    # -----------------------------------------
    # LOGIN CHECK
    # -----------------------------------------

    if "business_id" not in session:
        return redirect("/login")

    business_id = session["business_id"]

    # -----------------------------------------
    # GET THIS BUSINESS'S CUSTOMERS
    # -----------------------------------------

    customer_list = Customer.query.filter_by(
        business_id=business_id
    ).order_by(
        Customer.created_at.desc()
    ).all()

    # -----------------------------------------
    # CHECK IF EDITING
    # -----------------------------------------

    edit_id = request.args.get("edit")

    edit_customer = None

    if edit_id:

        try:

            edit_customer = Customer.query.filter_by(
                id=int(edit_id),
                business_id=business_id
            ).first()

        except (ValueError, TypeError):

            edit_customer = None

    # -----------------------------------------
    # RENDER
    # -----------------------------------------

    return render_template(
        "customers.html",
        customers=customer_list,
        edit_customer=edit_customer
    )


# =========================================
# ADD CUSTOMER
# =========================================

@customers.route(
    "/add-customer",
    methods=["POST"]
)
def add_customer():

    # -----------------------------------------
    # LOGIN CHECK
    # -----------------------------------------

    if "business_id" not in session:
        return redirect("/login")

    business_id = session["business_id"]

    # -----------------------------------------
    # GET FORM DATA
    # -----------------------------------------

    name = request.form.get(
        "name",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    # -----------------------------------------
    # VALIDATION
    # -----------------------------------------

    if not phone:

        flash(
            "Customer phone number is required."
        )

        return redirect("/customers")

    # -----------------------------------------
    # CHECK DUPLICATE
    # -----------------------------------------

    existing_customer = Customer.query.filter_by(
        business_id=business_id,
        phone=phone
    ).first()

    if existing_customer:

        flash(
            "A customer with this phone number already exists."
        )

        return redirect("/customers")

    # -----------------------------------------
    # CREATE CUSTOMER
    # -----------------------------------------

    customer = Customer(
        business_id=business_id,
        name=name,
        phone=phone
    )

    db.session.add(customer)
    db.session.commit()

    flash(
        "Customer added successfully."
    )

    return redirect("/customers")


# =========================================
# EDIT CUSTOMER
# =========================================

@customers.route(
    "/edit-customer/<int:customer_id>",
    methods=["POST"]
)
def edit_customer(customer_id):

    # -----------------------------------------
    # LOGIN CHECK
    # -----------------------------------------

    if "business_id" not in session:
        return redirect("/login")

    business_id = session["business_id"]

    # -----------------------------------------
    # FIND CUSTOMER
    # -----------------------------------------

    customer = Customer.query.filter_by(
        id=customer_id,
        business_id=business_id
    ).first()

    if not customer:

        flash(
            "Customer not found."
        )

        return redirect("/customers")

    # -----------------------------------------
    # GET FORM DATA
    # -----------------------------------------

    name = request.form.get(
        "name",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    # -----------------------------------------
    # VALIDATION
    # -----------------------------------------

    if not phone:

        flash(
            "Customer phone number is required."
        )

        return redirect(
            f"/customers?edit={customer_id}"
        )

    # -----------------------------------------
    # CHECK DUPLICATE PHONE
    # -----------------------------------------

    existing_customer = Customer.query.filter(
        Customer.business_id == business_id,
        Customer.phone == phone,
        Customer.id != customer_id
    ).first()

    if existing_customer:

        flash(
            "Another customer already uses this phone number."
        )

        return redirect(
            f"/customers?edit={customer_id}"
        )

    # -----------------------------------------
    # UPDATE
    # -----------------------------------------

    customer.name = name
    customer.phone = phone

    db.session.commit()

    flash(
        "Customer updated successfully."
    )

    return redirect("/customers")


# =========================================
# DELETE CUSTOMER
# =========================================

@customers.route(
    "/delete-customer/<int:customer_id>",
    methods=["POST"]
)
def delete_customer(customer_id):

    # -----------------------------------------
    # LOGIN CHECK
    # -----------------------------------------

    if "business_id" not in session:
        return redirect("/login")

    business_id = session["business_id"]

    # -----------------------------------------
    # FIND CUSTOMER
    # -----------------------------------------

    customer = Customer.query.filter_by(
        id=customer_id,
        business_id=business_id
    ).first()

    if not customer:

        flash(
            "Customer not found."
        )

        return redirect("/customers")

    # -----------------------------------------
    # DELETE
    # -----------------------------------------

    db.session.delete(customer)
    db.session.commit()

    flash(
        "Customer deleted successfully."
    )

    return redirect("/customers")
