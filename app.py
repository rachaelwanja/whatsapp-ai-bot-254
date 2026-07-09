from flask import Flask, render_template, request, redirect, session, flash, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from twilio.twiml.voice_response import VoiceResponse
from twilio.twiml.messaging_response import MessagingResponse

import os
import uuid
import requests
import base64

from werkzeug.utils import secure_filename

from models import db, Business, Appointment, Service, Payment

from services import (
    get_access_token,
    generate_password,
    stk_push,
    ask_ai
)

# =========================================
# BLUEPRINTS
# =========================================

from routes.auth import auth
from routes.dashboard import dashboard
from routes.services import services
from routes.appointments import appointments
from routes.customers import customers
from routes.payments import payments
from routes.whatsapp import whatsapp

# =========================================
# CREATE APP
# =========================================

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

app.config["UPLOAD_FOLDER"] = "static/uploads"

db.init_app(app)

# =========================================
# REGISTER BLUEPRINTS
# =========================================

app.register_blueprint(auth)
app.register_blueprint(dashboard)
app.register_blueprint(services)
app.register_blueprint(appointments)
app.register_blueprint(customers)
app.register_blueprint(payments)
app.register_blueprint(whatsapp)

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
    
# =========================================
# HOME
# =========================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )
@app.route("/debug-businesses")
def debug_businesses():

    businesses = Business.query.all()

    output = ""

    for b in businesses:
        output += f"{b.id} | {b.username}<br>"

    return output

@app.route("/users")
def users():

    businesses = Business.query.all()

    for b in businesses:
        print(
            b.id,
            b.username,
            b.business_name
        )

    return "Check Render logs"
    
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
# ANALYTICS
# =========================================

@app.route("/analytics")
def analytics():

    if "business_id" not in session:
        return redirect("/login")

    business = Business.query.get(
        session["business_id"]
    )

    appointments = Appointment.query.filter_by(
        business_id=business.id
    ).all()

    services = Service.query.filter_by(
        business_id=business.id
    ).all()

    payments = Payment.query.filter_by(
        business_id=business.id
    ).all()

    return render_template(
        "analytics.html",
        business=business,
        appointments=appointments,
        services=services,
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
    ).strip().lower()

    # Get business
    business = Business.query.first()

    if not business:

        response = MessagingResponse()
        response.message(
            "No business has been configured yet."
        )

        return Response(
            str(response),
            mimetype="text/xml"
        )

    # -----------------------------------
    # WELCOME MESSAGE
    # -----------------------------------

    if incoming_msg in [
        "hi",
        "hello",
        "hey",
        "start",
        "menu"
    ]:

        services = Service.query.filter_by(
            business_id=business.id
        ).all()

        if services:

            services_text = "\n".join(
                [
                    f"- {s.name}: KES {s.price} ({s.duration})"
                    for s in services
                ]
            )

        else:

            services_text = "No services configured."

        prompt = f"""
You are the official AI receptionist for this business.

Your job is to chat naturally with customers over WhatsApp exactly like a professional receptionist.

Business Name:
{business.business_name}

Business Type:
{business.business_type}

Location:
{business.location}

Opening Hours:
{business.opening_hours}

Available Services:

{services_text}

Additional Instructions:

{business.ai_prompt}

The customer has just started the conversation.

Welcome them warmly.

Introduce yourself as the business receptionist.

Explain that you can help with:
- Appointments
- Services
- Prices
- Location
- Opening hours

Do NOT show a numbered menu.

Keep your reply friendly, natural and under 80 words.
"""
print("========== SERVICES SENT TO AI ==========")
print(services_text)
        reply = ask_ai(prompt)

        response = MessagingResponse()

        response.message(reply)

        return Response(
            str(response),
            mimetype="text/xml"
        )

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
        
@app.route("/migrate-service")
def migrate_service():

    try:

        db.session.execute(db.text("""
            ALTER TABLE service
            ADD COLUMN IF NOT EXISTS category VARCHAR(100) DEFAULT 'General'
        """))

        db.session.execute(db.text("""
            ALTER TABLE service
            ADD COLUMN IF NOT EXISTS deposit INTEGER DEFAULT 0
        """))

        db.session.execute(db.text("""
            ALTER TABLE service
            ADD COLUMN IF NOT EXISTS image VARCHAR(500) DEFAULT ''
        """))

        db.session.execute(db.text("""
            ALTER TABLE service
            ADD COLUMN IF NOT EXISTS available BOOLEAN DEFAULT TRUE
        """))

        db.session.commit()

        return "Service migration successful"

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
