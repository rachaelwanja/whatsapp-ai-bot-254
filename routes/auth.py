from flask import Blueprint, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, Business

auth = Blueprint("auth", __name__)


# =========================================
# SIGNUP
# =========================================

@auth.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        business_name = request.form.get("business_name")
        business_phone = request.form.get("business_phone")

        existing_user = Business.query.filter_by(
            username=username
        ).first()

        if existing_user:

            flash("Account already exists")

            return redirect("/signup")

        hashed_password = generate_password_hash(password)

        new_business = Business(
            username=username,
            password=hashed_password,
            business_name=business_name,
            business_phone=business_phone
        )

        db.session.add(new_business)
        db.session.commit()

        flash("Signup successful")

        return redirect("/login")

    return render_template("signup.html")

# =========================================
# LOGIN
# =========================================

@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        business = Business.query.filter_by(
            username=username
        ).first()

        print("USERNAME:", username)
        print("BUSINESS:", business)
        print("ENTERED PASSWORD:", password)

        if business:
            print("STORED HASH:", business.password)
            print(
                "PASSWORD MATCH:",
                check_password_hash(
                    business.password,
                    password
                )
            )

        if business and check_password_hash(
            business.password,
            password
        ):

            session["business_id"] = business.id

            return redirect("/dashboard")

        flash("Invalid credentials")
        return redirect("/login")

    return render_template("login.html")

# =========================================
# LOGOUT
# =========================================

@auth.route("/logout")
def logout():

    session.clear()

    return redirect("/login")
