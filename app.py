from flask import Flask, render_template, request, redirect, session, flash, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from twilio.twiml.voice_response import VoiceResponse
import os
import requests
import base64
app = Flask(__name__)

# =========================================
# CONFIG
# =========================================

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "flowai-secret"
)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
# =========================================
# MPESA CONFIG
# =========================================

CONSUMER_KEY = os.getenv(
    "MPESA_CONSUMER_KEY"
)

CONSUMER_SECRET = os.getenv(
    "MPESA_CONSUMER_SECRET"
)

SHORTCODE = os.getenv(
    "MPESA_SHORTCODE"
)

PASSKEY = os.getenv(
    "MPESA_PASSKEY"
)

CALLBACK_URL = os.getenv(
    "CALLBACK_URL"
)
def get_access_token():

    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    response = requests.get(
        url,
        auth=(
            CONSUMER_KEY,
            CONSUMER_SECRET
        )
    )

    data = response.json()

    return data.get(
        "access_token"
    )

def generate_password():

    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S"
    )

    password = base64.b64encode(
        (
            SHORTCODE +
            PASSKEY +
            timestamp
        ).encode()
    ).decode()

    return password, timestamp

# =========================================
# DATABASE MODELS
# =========================================

class Business(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(200),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(500),
        nullable=False
    )

    business_name = db.Column(
        db.String(200)
    )

    business_phone = db.Column(
        db.String(100)
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class Service(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    business_id = db.Column(
        db.Integer
    )

    name = db.Column(
        db.String(200)
    )

    price = db.Column(
        db.Integer
    )

    duration = db.Column(
        db.Integer
    )


class Appointment(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    business_id = db.Column(
        db.Integer
    )

    customer_name = db.Column(
        db.String(200)
    )

    customer_phone = db.Column(
        db.String(100)
    )

    service = db.Column(
        db.String(200)
    )

    amount = db.Column(
        db.Integer,
        default=0
    )

    appointment_time = db.Column(
        db.String(100)
    )

    status = db.Column(
        db.String(50),
        default="confirmed"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

# =========================================
# HOME
# =========================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )

# =========================================
# SIGNUP
# =========================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form.get(
            "username"
        )

        password = request.form.get(
            "password"
        )

        business_name = request.form.get(
            "business_name"
        )

        business_phone = request.form.get(
            "business_phone"
        )

        existing_user = Business.query.filter_by(
            username=username
        ).first()

        if existing_user:

            flash(
                "Account already exists"
            )

            return redirect(
                "/signup"
            )

        hashed_password = generate_password_hash(
            password
        )

        new_business = Business(

            username=username,

            password=hashed_password,

            business_name=business_name,

            business_phone=business_phone

        )

        db.session.add(
            new_business
        )

        db.session.commit()

        flash(
            "Signup successful"
        )

        return redirect(
            "/login"
        )

    return render_template(
        "signup.html"
    )

# =========================================
# LOGIN
# =========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username"
        )

        password = request.form.get(
            "password"
        )

        business = Business.query.filter_by(
            username=username
        ).first()

        if business and check_password_hash(
            business.password,
            password
        ):

            session["business_id"] = business.id

            return redirect(
                "/dashboard"
            )

        flash(
            "Invalid credentials"
        )

        return redirect(
            "/login"
        )

    return render_template(
        "login.html"
    )

# =========================================
# DASHBOARD
# =========================================

@app.route("/dashboard")
def dashboard():

    if "business_id" not in session:

        return redirect(
            "/login"
        )

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

    total_revenue = sum(
        a.amount for a in appointments
    )

    return render_template(

        "dashboard.html",

        business=business,

        appointments=appointments,

        services=services,

        revenue=total_revenue

    )

# =========================================
# ADD SERVICE
# =========================================

@app.route("/add-service", methods=["POST"])
def add_service():

    service = Service(

        business_id=session["business_id"],

        name=request.form.get("name"),

        price=request.form.get("price"),

        duration=request.form.get("duration")

    )

    db.session.add(service)

    db.session.commit()

    return redirect("/dashboard")

# =========================================
# ADD APPOINTMENT
# =========================================

@app.route("/add-appointment", methods=["POST"])
def add_appointment():

    business_id = session["business_id"]

    appointment_time = request.form.get(
        "appointment_time"
    )

    existing = Appointment.query.filter_by(

        business_id=business_id,

        appointment_time=appointment_time

    ).first()

    if existing:

        flash(
            "Time slot already booked"
        )

        return redirect(
            "/dashboard"
        )

    appointment = Appointment(

        business_id=business_id,

        customer_name=request.form.get(
            "customer_name"
        ),

        customer_phone=request.form.get(
            "customer_phone"
        ),

        service=request.form.get(
            "service"
        ),

        amount=int(
            request.form.get("amount")
        ),

        appointment_time=appointment_time

    )

    db.session.add(
        appointment
    )

    db.session.commit()

    return redirect(
        "/dashboard"
    )

# =========================================
# CUSTOMERS PAGE
# =========================================

@app.route("/customers")
def customers():

    if "business_id" not in session:

        return redirect(
            "/login"
        )

    customers = Appointment.query.filter_by(
        business_id=session["business_id"]
    ).all()

    return render_template(

        "customers.html",

        customers=customers

    )

# =========================================
# WHATSAPP BOT
# =========================================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.form.get(
        "Body",
        ""
    ).lower()

    if "pay" in incoming_msg:

        access_token = get_access_token()

        reply = (
            "M-Pesa payment request initiated."
            if access_token
            else
            "Failed to connect to M-Pesa."
        )

    elif "hi" in incoming_msg or "hello" in incoming_msg:

        reply = "Hello 👋 Welcome to FlowAI Receptionist."

    elif "appointment" in incoming_msg:

        reply = "Please visit your dashboard to book an appointment."

    else:

        reply = "You said: " + incoming_msg

    twiml = f"""
<Response>
<Message>{reply}</Message>
</Response>
"""

    return Response(
        twiml,
        mimetype="text/xml"
    )

# =========================================
# LOGOUT
# =========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        "/login"
    )

# =========================================
# RESET DATABASE
# =========================================

@app.route("/reset-database")
def reset_database():

    try:

        db.session.execute(
            db.text(
                "DROP SCHEMA public CASCADE"
            )
        )

        db.session.execute(
            db.text(
                "CREATE SCHEMA public"
            )
        )

        db.session.commit()

        db.create_all()

        return "DATABASE RESET SUCCESSFUL"

    except Exception as e:

        db.session.rollback()

        return str(e)

# =========================================
# CREATE TABLES
# =========================================

with app.app_context():

    db.create_all()

# =========================================
# RUN APP
# =========================================

if __name__ == "__main__":

    app.run(debug=True)
