from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

import os
import datetime
import requests
import base64

# ==================================================
# APP CONFIG
# ==================================================

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "flowai_secret")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ==================================================
# DATABASE MODELS
# ==================================================

class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_name = db.Column(db.String(200))
    email = db.Column(db.String(200))
    phone = db.Column(db.String(30))
    password = db.Column(db.String(200))

    plan = db.Column(db.String(50), default="basic")

    opening_time = db.Column(db.String(20), default="08:00")
    closing_time = db.Column(db.String(20), default="18:00")

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(db.Integer)

    name = db.Column(db.String(200))
    price = db.Column(db.Integer)
    duration = db.Column(db.Integer)

    active = db.Column(db.Boolean, default=True)


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(db.Integer)

    customer_name = db.Column(db.String(200))
    phone = db.Column(db.String(30))

    service = db.Column(db.String(200))

    appointment_date = db.Column(db.String(100))
    appointment_time = db.Column(db.String(100))

    status = db.Column(db.String(50), default="Booked")

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(db.Integer)

    phone = db.Column(db.String(30))
    amount = db.Column(db.Integer)

    status = db.Column(db.String(50), default="Pending")

    mpesa_receipt = db.Column(db.String(200))

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class CallLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(db.Integer)

    caller = db.Column(db.String(30))

    transcript = db.Column(db.Text)

    ai_response = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# ==================================================
# HELPERS
# ==================================================

def logged_in():
    return "business_id" in session


def current_business():
    return Business.query.get(session["business_id"])


def slot_available(business_id, date, time):

    existing = Appointment.query.filter_by(
        business_id=business_id,
        appointment_date=date,
        appointment_time=time
    ).first()

    return existing is None


def inside_working_hours(business, appointment_time):

    opening = int(business.opening_time.split(":")[0])
    closing = int(business.closing_time.split(":")[0])

    booking_hour = int(appointment_time.split(":")[0])

    return opening <= booking_hour < closing

# ==================================================
# WHATSAPP CONFIRMATION
# ==================================================

def send_whatsapp_confirmation(phone, message):

    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )

    client.messages.create(
        from_='whatsapp:+14155238886',
        body=message,
        to=f'whatsapp:+{phone}'
    )

# ==================================================
# MPESA
# ==================================================

def get_access_token():

    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    response = requests.get(
        url,
        auth=(
            os.getenv("MPESA_CONSUMER_KEY"),
            os.getenv("MPESA_CONSUMER_SECRET")
        )
    )

    return response.json().get("access_token")


def stk_push(phone, amount):

    access_token = get_access_token()

    shortcode = os.getenv("MPESA_SHORTCODE")
    passkey = os.getenv("MPESA_PASSKEY")

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    password = base64.b64encode(
        (shortcode + passkey + timestamp).encode()
    ).decode()

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": os.getenv("CALLBACK_URL"),
        "AccountReference": "FlowAI",
        "TransactionDesc": "FlowAI Payment"
    }

    requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers=headers
    )

# ==================================================
# HOME
# ==================================================

@app.route("/")
def home():
    return render_template("index.html")

# ==================================================
# SIGNUP
# ==================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        business = Business(
            business_name=request.form.get("business_name"),
            email=request.form.get("email"),
            phone=request.form.get("phone"),
            password=request.form.get("password")
        )

        db.session.add(business)
        db.session.commit()

        return redirect("/login")

    return render_template("signup.html")

# ==================================================
# LOGIN
# ==================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        business = Business.query.filter_by(
            email=request.form.get("email"),
            password=request.form.get("password")
        ).first()

        if business:

            session["business_id"] = business.id

            return redirect("/dashboard")

    return render_template("login.html")

# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

# ==================================================
# DASHBOARD
# ==================================================

@app.route("/dashboard")
def dashboard():

    if not logged_in():
        return redirect("/login")

    business = current_business()

    appointments = Appointment.query.filter_by(
        business_id=business.id
    ).all()

    payments = Payment.query.filter_by(
        business_id=business.id
    ).all()

    services = Service.query.filter_by(
        business_id=business.id
    ).all()

    revenue = sum(
        [p.amount for p in payments if p.amount]
    )

    return render_template(
        "dashboard.html",
        business=business,
        appointments=appointments,
        payments=payments,
        services=services,
        revenue=revenue
    )

# ==================================================
# SERVICES
# ==================================================

@app.route("/services")
def services():

    if not logged_in():
        return redirect("/login")

    business = current_business()

    services = Service.query.filter_by(
        business_id=business.id
    ).all()

    return render_template(
        "services.html",
        services=services
    )


@app.route("/add-service", methods=["POST"])
def add_service():

    if not logged_in():
        return redirect("/login")

    business = current_business()

    service = Service(
        business_id=business.id,
        name=request.form.get("name"),
        price=request.form.get("price"),
        duration=request.form.get("duration")
    )

    db.session.add(service)
    db.session.commit()

    return redirect("/services")

# ==================================================
# APPOINTMENTS
# ==================================================

@app.route("/appointments")
def appointments():

    if not logged_in():
        return redirect("/login")

    business = current_business()

    appointments = Appointment.query.filter_by(
        business_id=business.id
    ).all()

    return render_template(
        "appointments.html",
        appointments=appointments
    )

# ==================================================
# CUSTOMERS
# ==================================================

@app.route("/customers")
def customers():

    if not logged_in():
        return redirect("/login")

    business = current_business()

    customers = Appointment.query.filter_by(
        business_id=business.id
    ).all()

    return render_template(
        "customers.html",
        customers=customers
    )

# ==================================================
# PAYMENTS
# ==================================================

@app.route("/payments")
def payments():

    if not logged_in():
        return redirect("/login")

    business = current_business()

    payments = Payment.query.filter_by(
        business_id=business.id
    ).all()

    return render_template(
        "payments.html",
        payments=payments
    )

# ==================================================
# SETTINGS
# ==================================================

@app.route("/settings")
def settings():

    if not logged_in():
        return redirect("/login")

    business = current_business()

    return render_template(
        "settings.html",
        business=business
    )

# ==================================================
# CALL LOGS
# ==================================================

@app.route("/call-logs")
def call_logs():

    if not logged_in():
        return redirect("/login")

    business = current_business()

    logs = CallLog.query.filter_by(
        business_id=business.id
    ).all()

    return render_template(
        "call_logs.html",
        logs=logs
    )

# ==================================================
# SUBSCRIPTIONS
# ==================================================

@app.route("/subscription")
def subscription():

    if not logged_in():
        return redirect("/login")

    business = current_business()

    return render_template(
        "subscription.html",
        business=business
    )

# ==================================================
# BOOK APPOINTMENT
# ==================================================

@app.route("/book", methods=["POST"])
def book():

    business = current_business()

    customer_name = request.form.get("customer_name")
    phone = request.form.get("phone")

    service = request.form.get("service")

    appointment_date = request.form.get("appointment_date")
    appointment_time = request.form.get("appointment_time")

    amount = int(request.form.get("amount"))

    # =========================
    # WORKING HOURS CHECK
    # =========================

    if not inside_working_hours(
        business,
        appointment_time
    ):

        return "Business closed at that time"

    # =========================
    # DOUBLE BOOKING CHECK
    # =========================

    if not slot_available(
        business.id,
        appointment_date,
        appointment_time
    ):

        return "Time slot already booked"

    # =========================
    # CREATE APPOINTMENT
    # =========================

    appointment = Appointment(
        business_id=business.id,
        customer_name=customer_name,
        phone=phone,
        service=service,
        appointment_date=appointment_date,
        appointment_time=appointment_time
    )

    db.session.add(appointment)
    db.session.commit()

    # =========================
    # MPESA STK PUSH
    # =========================

    stk_push(phone, amount)

    # =========================
    # WHATSAPP CONFIRMATION
    # =========================

    send_whatsapp_confirmation(
        phone,
        f"""
✅ Booking Confirmed

Service: {service}

Date: {appointment_date}

Time: {appointment_time}

Thank you for choosing FlowAI.
"""
    )

    # =========================
    # LIVE DASHBOARD NOTIFICATION
    # =========================

    socketio.emit(
        "new_notification",
        {
            "message": f"🔥 New booking from {customer_name}"
        }
    )

    return redirect("/appointments")

# ==================================================
# MPESA CALLBACK
# ==================================================

@app.route("/callback", methods=["POST"])
def callback():

    data = request.get_json()

    print(data)

    return jsonify({
        "ResultCode": 0
    })

# ==================================================
# WHATSAPP AI
# ==================================================

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming = request.values.get("Body", "").lower()

    response = MessagingResponse()

    if "hello" in incoming or "hi" in incoming:

        response.message(
            "👋 Welcome to FlowAI.\nHow can I help you today?"
        )

    elif "book" in incoming:

        response.message(
            "📅 Please send:\nService\nDate\nTime"
        )

    elif "price" in incoming:

        response.message(
            "💰 Basic KES 500\nPro KES 1000\nPremium KES 2000"
        )

    else:

        response.message(
            "🤖 FlowAI received your message."
        )

    return str(response)

# ==================================================
# VOICE AI
# ==================================================

@app.route("/voice", methods=["POST"])
def voice():

    response = VoiceResponse()

    gather = Gather(
        input="speech",
        action="/process-speech",
        method="POST"
    )

    gather.say(
        "Hello. Welcome to Flow AI. What service would you like to book?"
    )

    response.append(gather)

    return str(response)


@app.route("/process-speech", methods=["POST"])
def process_speech():

    speech = request.form.get("SpeechResult")

    response = VoiceResponse()

    ai_reply = f"""
You said {speech}.

Please provide your preferred date and time.
"""

    response.say(ai_reply)

    # SAVE CALL LOG

    log = CallLog(
        business_id=1,
        caller=request.form.get("From"),
        transcript=speech,
        ai_response=ai_reply
    )

    db.session.add(log)
    db.session.commit()

    return str(response)

# ==================================================
# SOCKET EVENTS
# ==================================================

@socketio.on("connect")
def connected():
    print("Client connected")

# ==================================================
# INIT DATABASE
# ==================================================

with app.app_context():
    db.create_all()

# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":
    socketio.run(app, debug=True)
