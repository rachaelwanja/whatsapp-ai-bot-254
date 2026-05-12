import os
import requests
from datetime import datetime, time

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify
)

from flask_sqlalchemy import SQLAlchemy
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client

# =====================================================
# APP CONFIG
# =====================================================

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "flowai-secret")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =====================================================
# ENVIRONMENT VARIABLES
# =====================================================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# =====================================================
# DATABASE MODELS
# =====================================================

class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_name = db.Column(db.String(200))
    email = db.Column(db.String(200), unique=True)
    password = db.Column(db.String(200))

    phone = db.Column(db.String(50))

    opening_time = db.Column(db.String(20), default="08:00")
    closing_time = db.Column(db.String(20), default="18:00")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(
        db.Integer,
        db.ForeignKey("business.id")
    )

    name = db.Column(db.String(200))
    phone = db.Column(db.String(50))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(
        db.Integer,
        db.ForeignKey("business.id")
    )

    name = db.Column(db.String(200))
    price = db.Column(db.Integer)
    duration = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(
        db.Integer,
        db.ForeignKey("business.id")
    )

    customer_name = db.Column(db.String(200))
    customer_phone = db.Column(db.String(50))

    service_name = db.Column(db.String(200))

    appointment_date = db.Column(db.String(50))
    appointment_time = db.Column(db.String(50))

    status = db.Column(db.String(50), default="Booked")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(
        db.Integer,
        db.ForeignKey("business.id")
    )

    customer_name = db.Column(db.String(200))
    phone = db.Column(db.String(50))

    amount = db.Column(db.Integer)

    status = db.Column(db.String(50), default="Pending")

    mpesa_receipt = db.Column(db.String(200))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CallLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(
        db.Integer,
        db.ForeignKey("business.id")
    )

    phone = db.Column(db.String(50))

    transcript = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =====================================================
# CREATE TABLES
# =====================================================

with app.app_context():
    db.create_all()

# =====================================================
# HELPERS
# =====================================================

def logged_in():
    return "business_id" in session


def current_business():
    if not logged_in():
        return None

    return Business.query.get(session["business_id"])


# =====================================================
# DOUBLE BOOKING PREVENTION
# =====================================================

def is_slot_available(
    business_id,
    appointment_date,
    appointment_time
):

    existing = Appointment.query.filter_by(
        business_id=business_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time
    ).first()

    return existing is None


# =====================================================
# WORKING HOURS CHECK
# =====================================================

def within_working_hours(business, appointment_time):

    opening = datetime.strptime(
        business.opening_time,
        "%H:%M"
    ).time()

    closing = datetime.strptime(
        business.closing_time,
        "%H:%M"
    ).time()

    selected = datetime.strptime(
        appointment_time,
        "%H:%M"
    ).time()

    return opening <= selected <= closing


# =====================================================
# ELEVENLABS VOICE
# =====================================================

def elevenlabs_tts(text):

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.85
        }
    }

    response = requests.post(
        url,
        json=data,
        headers=headers
    )

    audio_path = "static/voice.mp3"

    with open(audio_path, "wb") as f:
        f.write(response.content)

    return "/static/voice.mp3"


# =====================================================
# WHATSAPP CONFIRMATION
# =====================================================

def send_whatsapp_confirmation(phone, message):

    try:

        twilio_client.messages.create(
            from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
            body=message,
            to=f"whatsapp:{phone}"
        )

    except Exception as e:
        print(e)


# =====================================================
# ROUTES
# =====================================================

@app.route("/")
def index():
    return render_template("index.html")


# =====================================================
# SIGNUP
# =====================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        business = Business(
            business_name=request.form["business_name"],
            email=request.form["email"],
            password=request.form["password"],
            phone=request.form["phone"]
        )

        db.session.add(business)
        db.session.commit()

        flash("Account created successfully")

        return redirect("/login")

    return render_template("signup.html")


# =====================================================
# LOGIN
# =====================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        business = Business.query.filter_by(
            email=request.form["email"],
            password=request.form["password"]
        ).first()

        if business:

            session["business_id"] = business.id

            return redirect("/dashboard")

        flash("Invalid login")

    return render_template("login.html")


# =====================================================
# LOGOUT
# =====================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =====================================================
# DASHBOARD
# =====================================================

@app.route("/dashboard")
def dashboard():

    if not logged_in():
        return redirect("/login")

    business_id = session["business_id"]

    customers = Customer.query.filter_by(
        business_id=business_id
    ).all()

    appointments = Appointment.query.filter_by(
        business_id=business_id
    ).all()

    payments = Payment.query.filter_by(
        business_id=business_id
    ).all()

    total_revenue = sum(
        p.amount for p in payments if p.amount
    )

    return render_template(
        "dashboard.html",
        customers=customers,
        appointments=appointments,
        payments=payments,
        total_revenue=total_revenue
    )


# =====================================================
# SERVICES
# =====================================================

@app.route("/services")
def services():

    if not logged_in():
        return redirect("/login")

    services = Service.query.filter_by(
        business_id=session["business_id"]
    ).all()

    return render_template(
        "services.html",
        services=services
    )


@app.route("/add_service", methods=["POST"])
def add_service():

    service = Service(
        business_id=session["business_id"],
        name=request.form["name"],
        price=request.form["price"],
        duration=request.form["duration"]
    )

    db.session.add(service)
    db.session.commit()

    return redirect("/services")


# =====================================================
# APPOINTMENTS
# =====================================================

@app.route("/appointments")
def appointments():

    appointments = Appointment.query.filter_by(
        business_id=session["business_id"]
    ).all()

    return render_template(
        "appointments.html",
        appointments=appointments
    )


@app.route("/book_appointment", methods=["POST"])
def book_appointment():

    business = current_business()

    appointment_date = request.form["appointment_date"]
    appointment_time = request.form["appointment_time"]

    # CHECK WORKING HOURS

    if not within_working_hours(
        business,
        appointment_time
    ):

        flash("Outside working hours")

        return redirect("/appointments")

    # PREVENT DOUBLE BOOKINGS

    if not is_slot_available(
        business.id,
        appointment_date,
        appointment_time
    ):

        flash("Time slot already booked")

        return redirect("/appointments")

    appointment = Appointment(
        business_id=business.id,
        customer_name=request.form["customer_name"],
        customer_phone=request.form["customer_phone"],
        service_name=request.form["service_name"],
        appointment_date=appointment_date,
        appointment_time=appointment_time
    )

    db.session.add(appointment)
    db.session.commit()

    # WHATSAPP CONFIRMATION

    send_whatsapp_confirmation(
        request.form["customer_phone"],
        f"""
Hello {request.form['customer_name']}

Your appointment has been booked successfully.

Service: {request.form['service_name']}
Date: {appointment_date}
Time: {appointment_time}

Thank you for choosing us.
"""
    )

    flash("Appointment booked")

    return redirect("/appointments")


# =====================================================
# PAYMENTS
# =====================================================

@app.route("/payments")
def payments():

    payments = Payment.query.filter_by(
        business_id=session["business_id"]
    ).all()

    return render_template(
        "payments.html",
        payments=payments
    )


# =====================================================
# CUSTOMERS
# =====================================================

@app.route("/customers")
def customers():

    customers = Customer.query.filter_by(
        business_id=session["business_id"]
    ).all()

    return render_template(
        "customers.html",
        customers=customers
    )


# =====================================================
# CALL LOGS
# =====================================================

@app.route("/call_logs")
def call_logs():

    logs = CallLog.query.filter_by(
        business_id=session["business_id"]
    ).all()

    return render_template(
        "call_logs.html",
        logs=logs
    )


# =====================================================
# SETTINGS
# =====================================================

@app.route("/settings")
def settings():

    business = current_business()

    return render_template(
        "settings.html",
        business=business
    )


# =====================================================
# TWILIO VOICE AI
# =====================================================

@app.route("/voice", methods=["POST"])
def voice():

    response = VoiceResponse()

    audio_url = request.host_url[:-1] + elevenlabs_tts(
        "Habari. Karibu FlowAI. Tunaweza kukusaidia aje leo?"
    )

    response.play(audio_url)

    return str(response)


# =====================================================
# WHATSAPP WEBHOOK
# =====================================================

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming = request.values.get("Body", "")

    response_message = f"""
🤖 FlowAI received your message:

{incoming}
"""

    twilio_client.messages.create(
        from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
        body=response_message,
        to=request.values.get("From")
    )

    return "OK"


# =====================================================
# HEALTH CHECK
# =====================================================

@app.route("/health")
def health():
    return jsonify({
        "status": "running"
    })


# =====================================================
# RUN APP
# =====================================================

if __name__ == "__main__":
    app.run(debug=True)
