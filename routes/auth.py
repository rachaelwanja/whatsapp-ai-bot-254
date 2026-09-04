from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    flash,
    url_for
)

from email_service import send_email

from datetime import datetime, timedelta
import secrets
import os

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from models import (
    db,
    Business,
    PasswordResetToken
)

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

        username = request.form.get(
            "username",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        business = Business.query.filter_by(
            username=username
        ).first()

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
# PRIVACY POLICY
# =========================================

@auth.route("/privacy")
def privacy():
    return render_template("privacy.html")


# =========================================
# TERMS OF SERVICE
# =========================================

@auth.route("/terms")
def terms():
    return render_template("terms.html")


# =========================================
# FORGOT PASSWORD
# =========================================

@auth.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        business = Business.query.filter_by(
            email=email
        ).first()

        if business:

            # Generate secure reset token
            token = secrets.token_urlsafe(32)

            reset_token = PasswordResetToken(
                business_id=business.id,
                token=token,
                expires_at=datetime.utcnow()
                + timedelta(minutes=30)
            )

            db.session.add(reset_token)
            db.session.commit()

            # Create password reset link
            reset_link = url_for(
                "auth.reset_password",
                token=token,
                _external=True
            )

            # Email content
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Reset your FlowAI password</title>
            </head>

            <body style="
                margin: 0;
                padding: 0;
                background-color: #f4f7fb;
                font-family: Arial, sans-serif;
            ">

                <div style="
                    max-width: 600px;
                    margin: 40px auto;
                    background: white;
                    border-radius: 12px;
                    padding: 40px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                ">

                    <h1 style="
                        color: #111827;
                        margin-bottom: 10px;
                    ">
                        Reset your FlowAI password
                    </h1>

                    <p style="
                        color: #4b5563;
                        font-size: 16px;
                        line-height: 1.6;
                    ">
                        We received a request to reset the password
                        for your FlowAI account.
                    </p>

                    <p style="
                        color: #4b5563;
                        font-size: 16px;
                        line-height: 1.6;
                    ">
                        Click the button below to create a new password.
                    </p>

                    <div style="
                        margin: 30px 0;
                        text-align: center;
                    ">

                        <a href="{reset_link}"
                           style="
                               display: inline-block;
                               background: #111827;
                               color: white;
                               text-decoration: none;
                               padding: 14px 28px;
                               border-radius: 8px;
                               font-size: 16px;
                               font-weight: bold;
                           ">
                            Reset My Password
                        </a>

                    </div>

                    <p style="
                        color: #6b7280;
                        font-size: 14px;
                        line-height: 1.6;
                    ">
                        This link will expire in
                        <strong>30 minutes</strong>.
                    </p>

                    <p style="
                        color: #6b7280;
                        font-size: 14px;
                        line-height: 1.6;
                    ">
                        If you did not request a password reset,
                        you can safely ignore this email.
                    </p>

                    <hr style="
                        border: none;
                        border-top: 1px solid #e5e7eb;
                        margin: 30px 0;
                    ">

                    <p style="
                        color: #9ca3af;
                        font-size: 12px;
                        text-align: center;
                    ">
                        FlowAI — AI Business Automation
                    </p>

                </div>

            </body>
            </html>
            """

            # Send reset email
            try:

                send_email(
                    to=business.email,
                    subject="Reset your FlowAI password",
                    html=html
                )

            except Exception as e:

                print(
                    "PASSWORD RESET EMAIL ERROR:",
                    e
                )

        # IMPORTANT:
        # We show the same message whether the email exists or not.
        # This prevents people from discovering which emails
        # have FlowAI accounts.

        flash(
            "If an account exists with that email, "
            "a password reset link has been sent."
        )

        return redirect("/login")

    return render_template(
        "forgot_password.html"
    )

# =========================================
# RESET PASSWORD
# =========================================

@auth.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):

    reset_token = PasswordResetToken.query.filter_by(
        token=token,
        used=False
    ).first()

    if not reset_token:

        flash(
            "This password reset link is invalid."
        )

        return redirect("/login")

    if reset_token.expires_at < datetime.utcnow():

        flash(
            "This password reset link has expired."
        )

        return redirect("/forgot-password")

    business = Business.query.get(
        reset_token.business_id
    )

    if not business:

        flash(
            "Account not found."
        )

        return redirect("/login")

    if request.method == "POST":

        password = request.form.get(
            "password"
        )

        confirm_password = request.form.get(
            "confirm_password"
        )

        if not password:

            flash(
                "Please enter a new password."
            )

            return redirect(
                f"/reset-password/{token}"
            )

        if password != confirm_password:

            flash(
                "Passwords do not match."
            )

            return redirect(
                f"/reset-password/{token}"
            )

        business.password = generate_password_hash(
            password
        )

        reset_token.used = True

        db.session.commit()

        flash(
            "Password updated successfully. "
            "You can now log in."
        )

        return redirect("/login")

    return render_template(
        "reset_password.html",
        token=token
    )

# =========================================
# LOGOUT
# =========================================

@auth.route("/logout")
def logout():

    session.clear()

    return redirect("/login")
