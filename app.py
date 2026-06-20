from flask import Flask, render_template, request, redirect, session, flash, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from twilio.twiml.voice_response import VoiceResponse
import os
import requests
import base64
app = Flask(__name__)

booking_states = {}

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

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    if response.status_code != 200:
        return None

    try:
        data = response.json()
        return data.get("access_token")
    except Exception as e:
        print("JSON ERROR:", e)
        print("RAW RESPONSE:", response.text)
        return None
    

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


def stk_push(phone, amount):

    access_token = get_access_token()

    password, timestamp = generate_password()

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": "FlowAI",
        "TransactionDesc": "Payment"
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers
    )

    print("STK STATUS:", response.status_code)
    print("STK RESPONSE:", response.text)

    return response.json()
    
# =========================================
# OPENROUTER AI
# =========================================

def ask_ai(message):

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ]
        }
    )

    print(response.text)

    return response.json()["choices"][0]["message"]["content"]

# =========================================
# DATABASE MODELS
# =========================================
class Business(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        unique=True
    )

    password = db.Column(
        db.String(200)
    )

    business_name = db.Column(
        db.String(200)
    )

    business_type = db.Column(
        db.String(100),
        default="General"
    )

    business_phone = db.Column(
        db.String(50)
    )

    location = db.Column(
        db.String(300),
        default=""
    )

    opening_hours = db.Column(
        db.String(300),
        default=""
    )

    ai_prompt = db.Column(
        db.Text,
        default=""
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
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
@app.route("/migrate-business")
def migrate_business():

    try:

        db.session.execute(db.text("""
            ALTER TABLE business
            ADD COLUMN IF NOT EXISTS business_type VARCHAR(100) DEFAULT 'General'
        """))

        db.session.execute(db.text("""
            ALTER TABLE business
            ADD COLUMN IF NOT EXISTS location VARCHAR(300) DEFAULT ''
        """))

        db.session.execute(db.text("""
            ALTER TABLE business
            ADD COLUMN IF NOT EXISTS opening_hours VARCHAR(300) DEFAULT ''
        """))

        db.session.execute(db.text("""
            ALTER TABLE business
            ADD COLUMN IF NOT EXISTS ai_prompt TEXT DEFAULT ''
        """))

        db.session.commit()

        return "Business migration successful"

    except Exception as e:

        db.session.rollback()

        return str(e)
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

        print("USERNAME:", username)
        print("BUSINESS:", business)

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
    
@app.route("/business-settings", methods=["GET", "POST"])
def business_settings():

    if "business_id" not in session:
        return redirect("/login")

    business = Business.query.get(session["business_id"])

    if request.method == "POST":

        business.business_name = request.form.get("business_name")

        business.business_type = request.form.get("business_type")

        business.business_phone = request.form.get("business_phone")

        business.location = request.form.get("location")

        business.opening_hours = request.form.get("opening_hours")

        business.ai_prompt = request.form.get("ai_prompt")

        db.session.commit()

        flash("Business settings updated.")

        return redirect("/business-settings")

    return render_template(
        "business_settings.html",
        business=business
    )
    
# =========================================
# DASHBOARD
# =========================================

@app.route("/dashboard")
def dashboard():

    if "business_id" not in session:
        return redirect("/login")

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

    payments = Payment.query.order_by(
        Payment.id.desc()
    ).limit(5).all()

    total_revenue = sum(
        a.amount for a in appointments
    )

    customer_count = len(
        set(a.customer_phone for a in appointments)
    )

    return render_template(
        "dashboard.html",
        business=business,
        appointments=appointments,
        services=services,
        payments=payments,
        revenue=total_revenue,
        customer_count=customer_count
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
@app.route("/debug-users")
def debug_users():

    businesses = Business.query.all()

    output = ""

    for b in businesses:
        output += f"{b.id} - {b.username}<br>"

    return output
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
# PAYMENTS PAGE
# =========================================

@app.route("/payments")
def payments():

    if "business_id" not in session:

        return redirect(
            "/login"
        )

    payments = Payment.query.order_by(
        Payment.id.desc()
    ).all()

    return render_template(
        "payments.html",
        payments=payments
    ) 
    
# =========================================
# WHATSAPP BOT
# =========================================

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

incoming_msg = request.form.get(
    "Body",
    ""
).lower().strip()

business = Business.query.first()

if not business:
    reply = "No business has been configured yet."

# =========================================
# BOOKING STATE
# =========================================

elif incoming_msg in booking_states:

    state = booking_states[incoming_msg]

    reply = ask_ai(incoming_msg)

# =========================================
# MAIN MENU
# =========================================

elif incoming_msg in [
    "hi",
    "hello",
    "hey",
    "start",
    "menu"
]:

    reply = f"""

Hi! Welcome to {business.business_name}.

I'm here to help.

Please choose an option:

1. Book an appointment
2. View our prices
3. Get our location
4. Opening hours

You can also type:
prices
location
hours

To make an M-Pesa payment:
pay 100

How can I help you today?
"""

# =========================================
# OPTION 1
# =========================================

elif incoming_msg in [
    "1",
    "appointment",
    "book",
    "booking"
]:

    booking_states[incoming_msg] = {
        "step": "name"
    }

    reply = """

Great! I'd be happy to help you book an appointment.

May I have your full name?
"""

# =========================================
# OPTION 2
# =========================================

elif incoming_msg in [
    "2",
    "price",
    "prices",
    "pricing",
    "cost"
]:

    reply = """

Here's our current price list:

Haircut - KES 500
Shaving - KES 200
Beard Trim - KES 300

Would you like to book an appointment?

Reply YES.
"""

# =========================================
# OPTION 3
# =========================================

elif incoming_msg in [
    "3",
    "location",
    "address",
    "where are you",
    "where are you located"
]:

    reply = f"""

📍 {business.location}

Reply BOOK to schedule a visit.
"""

# =========================================
# OPTION 4
# =========================================

elif incoming_msg in [
    "4",
    "hours",
    "opening hours",
    "working hours",
    "open"
]:

    reply = f"""

Our opening hours:

{business.opening_hours}

How can I help you today?
"""

# =========================================
# PAYMENT
# =========================================

elif incoming_msg.startswith("pay"):

    parts = incoming_msg.split()

    if len(parts) == 2:

        try:

            amount = int(parts[1])

            if amount < 1:

                reply = "Minimum amount is KES 1."

            else:

                result = stk_push(
                    "254115126566",
                    amount
                )

                reply = f"M-Pesa payment request for KES {amount} sent. Please check your phone."

        except Exception:

            reply = "Use format: pay 100"

    else:

        reply = "Use format: pay 100"

# =========================================
# BOOK
# =========================================

elif incoming_msg.startswith("book"):

    reply = """

Thank you for choosing us.

Your appointment request has been received.

Our team will contact you shortly.
"""

elif incoming_msg == "yes":

    reply = """

Great!

To book an appointment, please reply with your full name.
"""

# =========================================
# OPENAI
# =========================================

else:

    reply = ask_ai(incoming_msg)

twiml = f"""

<Response>
    <Message>{reply}</Message>
</Response>
"""return Response(
    twiml,
    mimetype="text/xml"
)
                    

# =========================================
# MPESA CALLBACK
# =========================================

@app.route("/mpesa-callback", methods=["POST"])
def mpesa_callback():

    data = request.json

    print("MPESA CALLBACK:", data)

    try:

        callback = data["Body"]["stkCallback"]

        items = callback["CallbackMetadata"]["Item"]

        values = {}

        for item in items:
            values[item["Name"]] = item.get("Value")

        payment = Payment(
            phone=str(values.get("PhoneNumber")),
            amount=float(values.get("Amount")),
            receipt=str(values.get("MpesaReceiptNumber")),
            transaction_date=str(values.get("TransactionDate"))
        )

        db.session.add(payment)
        db.session.commit()

        print("PAYMENT SAVED")

    except Exception as e:

        print("SAVE ERROR:", e)

    return {
        "ResultCode": 0,
        "ResultDesc": "Accepted"
    }

# =========================================
# LOGOUT
# =========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

# =========================================
# RESET DATABASE
# =========================================

@app.route("/reset-database")
def reset_database():

    try:

        db.session.execute(
            db.text("DROP SCHEMA public CASCADE")
        )

        db.session.execute(
            db.text("CREATE SCHEMA public")
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
