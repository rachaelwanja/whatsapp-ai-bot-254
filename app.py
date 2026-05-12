from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime
import os

# ====================================
# APP CONFIG
# ====================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "flowai_secret_key"
)

app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = "Lax"

# DATABASE

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ====================================
# TWILIO
# ====================================

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

twilio_client = Client(
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN
)

# ====================================
# DATABASE MODELS
# ====================================

class Business(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(300),
        nullable=False
    )

    email = db.Column(
        db.String(200)
    )

    phone = db.Column(
        db.String(50)
    )

    plan = db.Column(
        db.String(50),
        default="Basic"
    )

    opening_time = db.Column(
        db.String(20),
        default="08:00"
    )

    closing_time = db.Column(
        db.String(20),
        default="18:00"
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

    appointment_date = db.Column(
        db.String(100)
    )

    appointment_time = db.Column(
        db.String(100)
    )

    status = db.Column(
        db.String(50),
        default="Booked"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

# ====================================
# HOME
# ====================================

@app.route('/')
def home():

    return render_template('index.html')

# ====================================
# SIGNUP
# ====================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        phone = request.form.get('phone')

        if not username or not password:
            return "Username and password required"

        existing = Business.query.filter_by(
            username=username
        ).first()

        if existing:
            return "Username already exists"

        new_business = Business(
            username=username,
            password=generate_password_hash(password),
            email=email,
            phone=phone
        )

        db.session.add(new_business)
        db.session.commit()

        return redirect('/login')

    return render_template('signup.html')

# ====================================
# LOGIN
# ====================================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return "Missing username or password"

        business = Business.query.filter_by(
            username=username
        ).first()

        if not business:
            return "User not found"

        if check_password_hash(
            business.password,
            password
        ):

            session['business_id'] = business.id

            return redirect('/dashboard')

        return "Invalid password"

    return render_template('login.html')

# ====================================
# LOGOUT
# ====================================

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

# ====================================
# DASHBOARD
# ====================================

@app.route('/dashboard')
def dashboard():

    if 'business_id' not in session:
        return redirect('/login')

    business = Business.query.get(
        session['business_id']
    )

    if not business:
        session.clear()
        return redirect('/login')

    appointments = Appointment.query.filter_by(
        business_id=business.id
    ).order_by(
        Appointment.created_at.desc()
    ).all()

    return render_template(
        'dashboard.html',
        business=business,
        appointments=appointments
    )

# ====================================
# BOOK APPOINTMENT
# ====================================

@app.route('/book', methods=['POST'])
def book():

    if 'business_id' not in session:
        return redirect('/login')

    business = Business.query.get(
        session['business_id']
    )

    customer_name = request.form.get('customer_name')
    customer_phone = request.form.get('customer_phone')
    service = request.form.get('service')

    appointment_date = request.form.get('appointment_date')
    appointment_time = request.form.get('appointment_time')

    if not customer_name:
        return "Customer name required"

    # DOUBLE BOOKING CHECK

    existing = Appointment.query.filter_by(
        business_id=business.id,
        appointment_date=appointment_date,
        appointment_time=appointment_time
    ).first()

    if existing:
        return "Time slot already booked"

    # WORKING HOURS CHECK

    booking_hour = int(
        appointment_time.split(":")[0]
    )

    opening_hour = int(
        business.opening_time.split(":")[0]
    )

    closing_hour = int(
        business.closing_time.split(":")[0]
    )

    if booking_hour < opening_hour:
        return "Outside working hours"

    if booking_hour >= closing_hour:
        return "Outside working hours"

    appointment = Appointment(
        business_id=business.id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        service=service,
        appointment_date=appointment_date,
        appointment_time=appointment_time
    )

    db.session.add(appointment)
    db.session.commit()

    # WHATSAPP CONFIRMATION

    try:

        if customer_phone:

            twilio_client.messages.create(
                from_=TWILIO_WHATSAPP_NUMBER,
                to=f"whatsapp:{customer_phone}",
                body=f"""
Hello {customer_name}

Your appointment has been booked successfully.

Service: {service}
Date: {appointment_date}
Time: {appointment_time}

Thank you for choosing us.
"""
            )

    except Exception as e:
        print("Twilio Error:", e)

    return redirect('/dashboard')

# ====================================
# WHATSAPP BOT
# ====================================

@app.route('/whatsapp', methods=['POST'])
def whatsapp():

    incoming_msg = request.values.get(
        'Body',
        ''
    )

    response = MessagingResponse()

    msg = response.message()

    reply = f"""
🤖 FlowAI received your message

{incoming_msg}
"""

    msg.body(reply)

    return str(response)

# ====================================
# VOICE
# ====================================

@app.route('/voice', methods=['GET', 'POST'])
def voice():

    return """
<Response>
<Say voice="Polly.Joanna">
Karibu Flow AI.
Receptionist wako wa Kiswahili yuko tayari kukusaidia.
</Say>
</Response>
"""

# ====================================
# CREATE DATABASE
# ====================================

with app.app_context():
    db.create_all()

# ====================================
# RUN
# ====================================

if __name__ == '__main__':

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
