from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    jsonify,
    Response
)

from flask_sqlalchemy import SQLAlchemy
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client as TwilioClient

from datetime import datetime, time
import requests
import os
import base64

# =========================================================
# APP CONFIG
# =========================================================

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "flowai-secret")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================================================
# TWILIO
# =========================================================

twilio_client = TwilioClient(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

TWILIO_WHATSAPP = "whatsapp:+14155238886"

# =========================================================
# DATABASE MODELS
# =========================================================

class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_name = db.Column(db.String(200))
    email = db.Column(db.String(200), unique=True)
    phone = db.Column(db.String(50))

    password = db.Column(db.String(200))

    plan = db.Column(db.String(50), default="Starter")

    opening_time = db.Column(db.String(20), default="08:00")
    closing_time = db.Column(db.String(20), default="18:00")

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


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(
        db.Integer,
        db.ForeignKey("business.id")
    )

    name = db.Column(db.String(200))
    phone = db.Column(db.String(50))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(
        db.Integer,
        db.ForeignKey("business.id")
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customer.id")
    )

    service_id = db.Column(
        db.Integer,
        db.ForeignKey("service.id")
    )

    appointment_date = db.Column(db.String(100))
    appointment_time = db.Column(db.String(100))

    status = db.Column(db.String(50), default="Booked")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(
        db.Integer,
        db.ForeignKey("business.id")
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customer.id")
    )

    amount = db.Column(db.Integer)

    phone = db.Column(db.String(50))

    status = db.Column(db.String(50), default="Pending")

    mpesa_receipt = db.Column(db.String(100))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CallLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(
        db.Integer,
        db.ForeignKey("business.id")
    )

    customer_phone = db.Column(db.String(50))

    transcript = db.Column(db.Text)

    ai_reply = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# =========================================================
# HELPERS
# =========================================================

def logged_in():
    return "business_id" in session


def current_business():
    return Business.query.get(session["business_id"])


def send_whatsapp(phone, message):

    try:

        twilio_client.messages.create(
            from_=TWILIO_WHATSAPP,
            body=message,
            to=f"whatsapp:+{phone}"
        )

    except Exception as e:
        print("WHATSAPP ERROR:", e)


def get_ai_reply(text):

    try:

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",

            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"
            },

            json={
                "model": "openai/gpt-4o-mini",

                "messages": [
                    {
                        "role": "system",
                        "content": """
                        You are FlowAI.

                        You are a friendly Kenyan AI receptionist.

                        You help customers:
                        - book appointments
                        - ask business questions
                        - confirm services
                        - talk naturally
                        """
                    },

                    {
                        "role": "user",
                        "content": text
                    }
                ]
            }
        )

        data = response.json()

        return data["choices"][0]["message"]["content"]

    except Exception as e:

        print("AI ERROR:", e)

        return "Hello 👋 How can I help you today?"


# =========================================================
# DOUBLE BOOKING PREVENTION
# =========================================================

def slot_available(business_id, date, appointment_time):

    existing = Appointment.query.filter_by(
        business_id=business_id,
        appointment_date=date,
        appointment_time=appointment_time
    ).first()

    return existing is None


# =========================================================
# WORKING HOURS CHECK
# =========================================================

def within_working_hours(business, appointment_time):

    try:

        open_time = datetime.strptime(
            business.opening_time,
            "%H:%M"
        ).time()

        close_time = datetime.strptime(
            business.closing_time,
            "%H:%M"
        ).time()

        check_time = datetime.strptime(
            appointment_time,
            "%H:%M"
        ).time()

        return open_time <= check_time <= close_time

    except:
        return False


# =========================================================
# MPESA
# =========================================================

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

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

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
        "TransactionDesc": "Appointment Payment"
    }

    requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers=headers
    )

# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")

# =========================================================
# SIGNUP
# =========================================================

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

# =========================================================
# LOGIN
# =========================================================

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

# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

# =========================================================
# DASHBOARD
# =========================================================

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

    customers = Customer.query.filter_by(
        business_id=business.id
    ).all()

    revenue = sum([
        p.amount or 0 for p in payments
    ])

    return render_template(
        "dashboard.html",

        business=business,

        appointments=appointments,

        payments=payments,

        customers=customers,

        revenue=revenue
    )

# =========================================================
# SERVICES
# =========================================================

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

# =========================================================
# APPOINTMENTS
# =========================================================

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

# =========================================================
# CUSTOMERS
# =========================================================

@app.route("/customers")
def customers():

    if not logged_in():
        return redirect("/login")

    business = current_business()

    customers = Customer.query.filter_by(
        business_id=business.id
    ).all()

    return render_template(
        "customers.html",
        customers=customers
    )

# =========================================================
# PAYMENTS
# =========================================================

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

# =========================================================
# CALL LOGS
# =========================================================

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

# =========================================================
# SETTINGS
# =========================================================

@app.route("/settings")
def settings():

    if not logged_in():
        return redirect("/login")

    business = current_business()

    return render_template(
        "settings.html",
        business=business
    )

# =========================================================
# WHATSAPP AI
# =========================================================

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming = request.values.get("Body", "")
    phone = request.values.get("From", "")

    clean_phone = phone.replace("whatsapp:+", "")

    ai_reply = get_ai_reply(incoming)

    msg = VoiceResponse()
    response = MessagingResponse()

    response.message(ai_reply)

    return Response(
        str(response),
        mimetype="application/xml"
    )

# =========================================================
# TWILIO VOICE AI
# =========================================================

@app.route("/voice", methods=["POST"])
def voice():

    response = VoiceResponse()

    gather = Gather(
        input="speech",
        action="/process-speech",
        method="POST"
    )

    gather.say(
        "Hello. Welcome to Flow AI. How can I help you today?"
    )

    response.append(gather)

    return str(response)


@app.route("/process-speech", methods=["POST"])
def process_speech():

    speech = request.form.get("SpeechResult")

    response = VoiceResponse()

    ai_reply = get_ai_reply(speech)

    response.say(ai_reply)

    return str(response)

# =========================================================
# MPESA CALLBACK
# =========================================================

@app.route("/callback", methods=["POST"])
def callback():

    print(request.json)

    return jsonify({
        "ResultCode": 0,
        "ResultDesc": "Accepted"
    })

# =========================================================
# DATABASE INIT
# =========================================================

with app.app_context():

    db.create_all()

    print("✅ Database ready")

# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(debug=True)
