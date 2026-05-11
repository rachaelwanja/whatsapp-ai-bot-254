from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from twilio.twiml.voice_response import VoiceResponse, Gather

import requests
import datetime
import os
import base64

# =========================================
# APP
# =========================================
app = Flask(__name__)
app.secret_key = "secret"

# =========================================
# SOCKET
# =========================================
socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)

# =========================================
# DATABASE
# =========================================
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================================
# BUSINESS
# =========================================
class Business(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(db.String(100))

    industry = db.Column(db.String(100))

    phone = db.Column(db.String(20))

    opening_time = db.Column(
        db.String(20),
        default="08:00"
    )

    closing_time = db.Column(
        db.String(20),
        default="18:00"
    )

    active = db.Column(
        db.Boolean,
        default=True
    )

# =========================================
# CLIENT
# =========================================
class Client(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    business_id = db.Column(db.Integer)

    name = db.Column(db.String(100))

    phone = db.Column(db.String(20))

    username = db.Column(db.String(50))

    password = db.Column(db.String(50))

    expiry = db.Column(db.Date)

# =========================================
# SERVICE
# =========================================
class Service(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    business_id = db.Column(db.Integer)

    name = db.Column(db.String(100))

    price = db.Column(db.Integer)

    duration = db.Column(db.Integer)

    active = db.Column(
        db.Boolean,
        default=True
    )

# =========================================
# APPOINTMENT
# =========================================
class Appointment(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    business_id = db.Column(db.Integer)

    phone = db.Column(db.String(20))

    service = db.Column(db.String(100))

    date = db.Column(db.String(100))

    time = db.Column(db.String(100))

# =========================================
# PAYMENT
# =========================================
class Payment(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    business_id = db.Column(db.Integer)

    phone = db.Column(db.String(20))

    amount = db.Column(db.Integer)

    status = db.Column(
        db.String(20),
        default="pending"
    )

    mpesa_receipt = db.Column(
        db.String(100)
    )

    date = db.Column(db.String(100))

# =========================================
# CALL LOG
# =========================================
class CallLog(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    business_id = db.Column(db.Integer)

    phone = db.Column(db.String(20))

    role = db.Column(db.String(20))

    message = db.Column(db.String(500))

    date = db.Column(db.String(100))

# =========================================
# HELPERS
# =========================================
def require_login():

    return "client_id" in session

def get_client():

    return Client.query.get(
        session.get("client_id")
    )

# =========================================
# AVAILABILITY
# =========================================
def check_availability(
    business_id,
    date,
    time
):

    existing = Appointment.query.filter_by(
        business_id=business_id,
        date=date,
        time=time
    ).first()

    return existing is None

# =========================================
# MPESA
# =========================================
def get_access_token():

    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    res = requests.get(
        url,
        auth=(
            os.getenv("MPESA_CONSUMER_KEY"),
            os.getenv("MPESA_CONSUMER_SECRET")
        )
    )

    return res.json().get(
        "access_token"
    )

def stk_push(phone, amount):

    access_token = get_access_token()

    shortcode = os.getenv(
        "MPESA_SHORTCODE"
    )

    passkey = os.getenv(
        "MPESA_PASSKEY"
    )

    callback_url = os.getenv(
        "CALLBACK_URL"
    )

    timestamp = datetime.datetime.now().strftime(
        "%Y%m%d%H%M%S"
    )

    password = base64.b64encode(
        (
            shortcode +
            passkey +
            timestamp
        ).encode()
    ).decode()

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    headers = {
        "Authorization":
        f"Bearer {access_token}"
    }

    payload = {

        "BusinessShortCode": shortcode,

        "Password": password,

        "Timestamp": timestamp,

        "TransactionType":
        "CustomerPayBillOnline",

        "Amount": amount,

        "PartyA": phone,

        "PartyB": shortcode,

        "PhoneNumber": phone,

        "CallBackURL": callback_url,

        "AccountReference":
        "FlowAI",

        "TransactionDesc":
        "Booking Payment"
    }

    requests.post(
        url,
        json=payload,
        headers=headers
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
@app.route(
    "/signup",
    methods=["GET", "POST"]
)
def signup():

    if request.method == "POST":

        business = Business(

            name=request.form.get(
                "business_name"
            ),

            industry=request.form.get(
                "industry"
            ),

            phone=request.form.get(
                "phone"
            )
        )

        db.session.add(
            business
        )

        db.session.commit()

        client = Client(

            business_id=business.id,

            name=request.form.get(
                "name"
            ),

            phone=request.form.get(
                "phone"
            ),

            username=request.form.get(
                "username"
            ),

            password=request.form.get(
                "password"
            ),

            expiry=datetime.date.today() +
            datetime.timedelta(days=30)
        )

        db.session.add(client)

        db.session.commit()

        return redirect("/login")

    return render_template(
        "signup.html"
    )

# =========================================
# LOGIN
# =========================================
@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        client = Client.query.filter_by(

            username=request.form.get(
                "username"
            ),

            password=request.form.get(
                "password"
            )

        ).first()

        if client:

            session["client_id"] = client.id

            return redirect(
                "/dashboard"
            )

    return render_template(
        "login.html"
    )

# =========================================
# LOGOUT
# =========================================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

# =========================================
# DASHBOARD
# =========================================
@app.route("/dashboard")
def dashboard():

    if not require_login():

        return redirect("/login")

    client = get_client()

    payments = Payment.query.filter_by(
        business_id=client.business_id
    ).all()

    appointments = Appointment.query.filter_by(
        business_id=client.business_id
    ).all()

    logs = CallLog.query.filter_by(
        business_id=client.business_id
    ).order_by(
        CallLog.id.desc()
    ).limit(10).all()

    revenue = sum(
        p.amount or 0
        for p in payments
        if p.status == "paid"
    )

    chart_labels = [
        p.date[:10]
        for p in payments
    ]

    chart_data = [
        p.amount
        for p in payments
    ]

    return render_template(

        "dashboard.html",

        revenue=revenue,

        total_customers=len(
            appointments
        ),

        total_bookings=len(
            appointments
        ),

        total_payments=len(
            payments
        ),

        payments=payments,

        logs=logs,

        chart_labels=chart_labels,

        chart_data=chart_data
    )

# =========================================
# APPOINTMENTS
# =========================================
@app.route("/appointments")
def appointments():

    if not require_login():

        return redirect("/login")

    client = get_client()

    appointments = Appointment.query.filter_by(
        business_id=client.business_id
    ).all()

    return render_template(
        "appointments.html",
        appointments=appointments
    )

# =========================================
# CUSTOMERS
# =========================================
@app.route("/customers")
def customers():

    if not require_login():

        return redirect("/login")

    client = get_client()

    customers = Appointment.query.filter_by(
        business_id=client.business_id
    ).all()

    return render_template(
        "customers.html",
        customers=customers
    )

# =========================================
# PAYMENTS
# =========================================
@app.route("/payments")
def payments():

    if not require_login():

        return redirect("/login")

    client = get_client()

    payments = Payment.query.filter_by(
        business_id=client.business_id
    ).all()

    return render_template(
        "payments.html",
        payments=payments
    )

# =========================================
# SERVICES
# =========================================
@app.route("/services")
def services():

    if not require_login():

        return redirect("/login")

    client = get_client()

    services = Service.query.filter_by(
        business_id=client.business_id
    ).all()

    return render_template(
        "services.html",
        services=services
    )

# =========================================
# CREATE SERVICE
# =========================================
@app.route(
    "/services/create",
    methods=["POST"]
)
def create_service():

    client = get_client()

    service = Service(

        business_id=client.business_id,

        name=request.form.get(
            "name"
        ),

        price=int(
            request.form.get("price")
        ),

        duration=int(
            request.form.get("duration")
        )
    )

    db.session.add(service)

    db.session.commit()

    return redirect("/services")

# =========================================
# CALL LOGS
# =========================================
@app.route("/call_logs")
def call_logs():

    if not require_login():

        return redirect("/login")

    client = get_client()

    logs = CallLog.query.filter_by(
        business_id=client.business_id
    ).order_by(
        CallLog.id.desc()
    ).all()

    return render_template(
        "call_logs.html",
        logs=logs
    )

# =========================================
# SUBSCRIPTION
# =========================================
@app.route("/subscription")
def subscription():

    if not require_login():

        return redirect("/login")

    client = get_client()

    return render_template(
        "subscription.html",
        client=client
    )

# =========================================
# SETTINGS
# =========================================
@app.route("/settings")
def settings():

    if not require_login():

        return redirect("/login")

    client = get_client()

    business = Business.query.get(
        client.business_id
    )

    return render_template(
        "settings.html",
        business=business
    )

# =========================================
# UPDATE HOURS
# =========================================
@app.route(
    "/settings/hours",
    methods=["POST"]
)
def update_hours():

    client = get_client()

    business = Business.query.get(
        client.business_id
    )

    business.opening_time = request.form.get(
        "opening_time"
    )

    business.closing_time = request.form.get(
        "closing_time"
    )

    db.session.commit()

    return redirect("/settings")

# =========================================
# CALLBACK
# =========================================
@app.route(
    "/callback",
    methods=["POST"]
)
def callback():

    data = request.get_json()

    try:

        result = data["Body"]["stkCallback"]

        if result["ResultCode"] == 0:

            metadata = result[
                "CallbackMetadata"
            ]["Item"]

            amount = next(
                i["Value"]
                for i in metadata
                if i["Name"] == "Amount"
            )

            phone = next(
                i["Value"]
                for i in metadata
                if i["Name"] == "PhoneNumber"
            )

            receipt = next(
                i["Value"]
                for i in metadata
                if i["Name"] == "MpesaReceiptNumber"
            )

            payment = Payment.query.filter_by(
                phone=str(phone),
                status="pending"
            ).first()

            if payment:

                payment.status = "paid"

                payment.mpesa_receipt = receipt

                db.session.commit()

                socketio.emit(
                    "new_payment",
                    {
                        "message":
                        f"💰 New payment KES {amount}"
                    }
                )

    except Exception as e:

        print(e)

    return "OK"

# =========================================
# VOICE AI
# =========================================
sessions = {}

@app.route(
    "/voice",
    methods=["POST"]
)
def voice():

    business_id = 1

    socketio.emit(
        "call_status",
        {
            "message":
            "📞 Incoming customer call"
        }
    )

    response = VoiceResponse()

    call_id = request.values.get(
        "CallSid"
    )

    speech = request.values.get(
        "SpeechResult"
    )

    if call_id not in sessions:

        sessions[call_id] = {
            "step": "service"
        }

    current = sessions[call_id]

    # FIRST MESSAGE
    if not speech:

        gather = Gather(
            input="speech",
            action="/voice",
            method="POST"
        )

        gather.say(
            "Hello! Welcome to Flow AI. "
            "What service would you like?"
        )

        response.append(gather)

        return str(response)

    speech = speech.lower()

    # SAVE CUSTOMER LOG
    user_log = CallLog(

        business_id=business_id,

        phone=request.values.get(
            "From"
        ),

        role="customer",

        message=speech,

        date=str(
            datetime.datetime.now()
        )
    )

    db.session.add(user_log)

    db.session.commit()

    # STEP 1
    if current["step"] == "service":

        current["service"] = speech

        current["step"] = "date"

        ai_text = "What date would you like?"

        ai_log = CallLog(

            business_id=business_id,

            phone=request.values.get(
                "From"
            ),

            role="AI",

            message=ai_text,

            date=str(
                datetime.datetime.now()
            )
        )

        db.session.add(ai_log)

        db.session.commit()

        gather = Gather(
            input="speech",
            action="/voice",
            method="POST"
        )

        gather.say(ai_text)

        response.append(gather)

        return str(response)

    # STEP 2
    elif current["step"] == "date":

        current["date"] = speech

        current["step"] = "time"

        ai_text = "What time works for you?"

        ai_log = CallLog(

            business_id=business_id,

            phone=request.values.get(
                "From"
            ),

            role="AI",

            message=ai_text,

            date=str(
                datetime.datetime.now()
            )
        )

        db.session.add(ai_log)

        db.session.commit()

        gather = Gather(
            input="speech",
            action="/voice",
            method="POST"
        )

        gather.say(ai_text)

        response.append(gather)

        return str(response)

    # STEP 3
    elif current["step"] == "time":

        current["time"] = speech

        available = check_availability(
            business_id,
            current["date"],
            current["time"]
        )

        if not available:

            response.say(
                "Sorry, that slot is already booked."
            )

            return str(response)

        phone = request.values.get(
            "From"
        ).replace("+", "")

        appointment = Appointment(

            business_id=business_id,

            phone=phone,

            service=current["service"],

            date=current["date"],

            time=current["time"]
        )

        db.session.add(
            appointment
        )

        db.session.commit()

        # PAYMENT
        payment = Payment(

            business_id=business_id,

            phone=phone,

            amount=1000,

            status="pending",

            date=str(
                datetime.datetime.now()
            )
        )

        db.session.add(payment)

        db.session.commit()

        # STK PUSH
        stk_push(
            phone,
            1000
        )

        # LIVE BOOKING
        socketio.emit(
            "new_booking",
            {
                "message":
                f"📅 New booking for {current['service']}"
            }
        )

        response.say(
            "Your appointment has been booked successfully. "
            "We have sent payment request to your phone."
        )

        sessions.pop(call_id)

        return str(response)

# =========================================
# INIT
# =========================================
with app.app_context():

    db.create_all()

# =========================================
# RUN
# =========================================
if __name__ == "__main__":

    socketio.run(
        app,
        debug=True
    )
