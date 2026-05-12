from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests
import os

# =========================================
# APP CONFIG
# =========================================

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "flowai-secret")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================================
# DATABASE MODELS
# =========================================

class Business(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    business_name = db.Column(
        db.String(255)
    )

    business_phone = db.Column(
        db.String(50)
    )

    plan = db.Column(
        db.String(50),
        default="free"
    )

    opening_time = db.Column(
        db.String(20),
        default="08:00"
    )

    closing_time = db.Column(
        db.String(20),
        default="17:00"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class Booking(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    customer_name = db.Column(db.String(255))

    customer_phone = db.Column(db.String(50))

    booking_date = db.Column(db.String(50))

    booking_time = db.Column(db.String(50))

    service = db.Column(db.String(255))

    business_id = db.Column(db.Integer)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

# =========================================
# CREATE DATABASE
# =========================================

with app.app_context():
    db.create_all()

# =========================================
# TEMPORARY DATABASE RESET ROUTE
# =========================================

@app.route("/reset-database")
def reset_database():

    db.drop_all()

    db.create_all()

    return "✅ Database reset successful"

# =========================================
# HOME
# =========================================

@app.route("/")
def home():

    return render_template("index.html")

# =========================================
# SIGNUP
# =========================================

@app.route("/signup", methods=["GET", "POST"])
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
            return "❌ Username already exists"

        hashed_password = generate_password_hash(password)

        new_business = Business(
            username=username,
            password=hashed_password,
            business_name=business_name,
            business_phone=business_phone
        )

        db.session.add(new_business)

        db.session.commit()

        return redirect("/login")

    return render_template("signup.html")

# =========================================
# LOGIN
# =========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")

        password = request.form.get("password")

        business = Business.query.filter_by(
            username=username
        ).first()

        if not business:
            return "❌ Invalid username"

        if not check_password_hash(
            business.password,
            password
        ):
            return "❌ Invalid password"

        session["business_id"] = business.id

        return redirect("/dashboard")

    return render_template("login.html")

# =========================================
# DASHBOARD
# =========================================

@app.route("/dashboard")
def dashboard():

    if "business_id" not in session:
        return redirect("/login")

    business = Business.query.get(
        session["business_id"]
    )

    bookings = Booking.query.filter_by(
        business_id=business.id
    ).all()

    return render_template(
        "dashboard.html",
        business=business,
        bookings=bookings
    )

# =========================================
# LOGOUT
# =========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

# =========================================
# WHATSAPP WEBHOOK
# =========================================

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get(
        "Body",
        ""
    ).lower()

    sender = request.values.get(
        "From",
        ""
    )

    response_message = (
        "🤖 FlowAI received your message."
    )

    if "book" in incoming_msg:

        response_message = (
            "📅 Booking request received.\n"
            "Send your:\n"
            "1. Name\n"
            "2. Date\n"
            "3. Time"
        )

    elif (
        "hello" in incoming_msg
        or
        "hi" in incoming_msg
    ):

        response_message = (
            "👋 Karibu FlowAI.\n"
            "How can I help you today?"
        )

    send_whatsapp_message(
        sender,
        response_message
    )

    return "OK", 200

# =========================================
# SEND WHATSAPP MESSAGE
# =========================================

def send_whatsapp_message(to, body):

    account_sid = os.getenv(
        "TWILIO_ACCOUNT_SID"
    )

    auth_token = os.getenv(
        "TWILIO_AUTH_TOKEN"
    )

    whatsapp_number = os.getenv(
        "TWILIO_WHATSAPP_NUMBER"
    )

    url = (
        f"https://api.twilio.com/2010-04-01/"
        f"Accounts/{account_sid}/Messages.json"
    )

    data = {
        "From": whatsapp_number,
        "To": to,
        "Body": body
    }

    requests.post(
        url,
        data=data,
        auth=(account_sid, auth_token)
    )

# =========================================
# ELEVENLABS VOICE
# =========================================

@app.route("/speak", methods=["POST"])
def speak():

    data = request.get_json()

    text = data.get("text")

    api_key = os.getenv(
        "ELEVENLABS_API_KEY"
    )

    voice_id = os.getenv(
        "ELEVENLABS_VOICE_ID"
    )

    url = (
        f"https://api.elevenlabs.io/v1/"
        f"text-to-speech/{voice_id}"
    )

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2"
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers
    )

    return response.content

# =========================================
# HEALTH CHECK
# =========================================

@app.route("/health")
def health():

    return jsonify({
        "status": "running"
    })

# =========================================
# START APP
# =========================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
    )
