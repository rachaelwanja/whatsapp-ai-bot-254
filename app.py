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
# WHATSAPP AI
# =========================================

@app.route("/whatsapp-ai")
def whatsapp_ai():

    if "business_id" not in session:
        return redirect("/login")

    business = Business.query.get(
        session["business_id"]
    )

    return render_template(
        "whatsapp_ai.html",
        business=business
    )
    
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
# EDIT SERVICE
# =========================================

@app.route("/edit-service/<int:id>", methods=["GET", "POST"])
def edit_service(id):

    if "business_id" not in session:
        return redirect("/login")

    service = Service.query.filter_by(
        id=id,
        business_id=session["business_id"]
    ).first_or_404()

    if request.method == "POST":

        service.name = request.form["name"]
        service.category = request.form["category"]
        service.price = request.form["price"]
        service.duration = request.form["duration"]
        service.deposit = request.form["deposit"]
        service.image = request.form["image"]

        service.available = (
            "available" in request.form
        )

        db.session.commit()

        flash("Service updated successfully!")

        return redirect("/services")

    return render_template(
        "edit_service.html",
        service=service
    )
    
# =========================================
# DELETE SERVICE
# =========================================

@app.route("/delete-service/<int:id>")
def delete_service(id):

    if "business_id" not in session:
        return redirect("/login")

    service = Service.query.filter_by(
        id=id,
        business_id=session["business_id"]
    ).first_or_404()

    db.session.delete(service)
    db.session.commit()

    flash("Service deleted successfully!")

    return redirect("/services")
    
@app.route("/business-settings", methods=["GET", "POST"])
def business_settings():

    if "business_id" not in session:
        return redirect("/login")

    business = Business.query.get(
        session["business_id"]
    )

    if request.method == "POST":

        business.business_name = request.form.get(
            "business_name"
        )

        business.business_type = request.form.get(
            "business_type"
        )

        business.business_phone = request.form.get(
            "business_phone"
        )

        business.location = request.form.get(
            "location"
        )

        business.opening_hours = request.form.get(
            "opening_hours"
        )

        business.ai_prompt = request.form.get(
            "ai_prompt"
        )

        db.session.commit()

        flash("Business settings saved!")

        return redirect(
            "/business-settings"
        )

    return render_template(
        "business_settings.html",
        business=business
    )
    
# =========================================
# ADD SERVICE
# =========================================

@app.route("/add-service", methods=["POST"])
def add_service():

    if "business_id" not in session:
        return redirect("/login")

    # -----------------------------
    # Upload image
    # -----------------------------

    image_name = ""

    image = request.files.get("image")

    if image and image.filename != "":

        filename = secure_filename(
            image.filename
        )

        extension = filename.rsplit(
            ".", 1
        )[1].lower()

        image_name = (
            str(uuid.uuid4())
            + "."
            + extension
        )

        image.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                image_name
            )
        )

    # -----------------------------
    # Save service
    # -----------------------------

    service = Service(

        business_id=session["business_id"],

        name=request.form["name"],

        category=request.form["category"],

        price=int(request.form["price"]),

        duration=request.form["duration"],

        deposit=int(
            request.form.get("deposit", 0)
        ),

        image=image_name,

        available="available" in request.form

    )

    db.session.add(service)

    db.session.commit()

    flash(
        "Service added successfully!"
    )

    return redirect("/services")
# =========================================
# APPOINTMENTS
# =========================================

@app.route("/appointments")
def appointments():

    if "business_id" not in session:
        return redirect("/login")

    business_id = session["business_id"]

    business = Business.query.get(
        business_id
    )

    appointments = Appointment.query.filter_by(
        business_id=business_id
    ).order_by(
        Appointment.created_at.desc()
    ).all()

    return render_template(
        "appointments.html",
        business=business,
        appointments=appointments
    )
    
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
    # MAIN MENU
    # -----------------------------------

    if incoming_msg in [
        "hi",
        "hello",
        "hey",
        "start",
        "menu"
    ]:

        reply = f"""
Welcome to {business.business_name} 👋

Business Type:
{business.business_type}

Please choose an option:

1. Book Appointment
2. Services & Prices
3. Location
4. Opening Hours

Or ask me anything.
"""

    # -----------------------------------
    # BOOK APPOINTMENT
    # -----------------------------------

    elif incoming_msg in [
        "1",
        "book",
        "booking",
        "appointment"
    ]:

        reply = """
Great 😊

Please tell me:

• Your name
• Service
• Preferred date
• Preferred time
"""

    # -----------------------------------
    # SERVICES
    # -----------------------------------

    elif incoming_msg in [
        "2",
        "services",
        "prices"
    ]:

        services = Service.query.filter_by(
            business_id=business.id
        ).all()

        if services:

            reply = "Our Services:\n\n"

            for service in services:

                reply += (
                    f"• {service.name}"
                    f" - KES {service.price}\n"
                )

        else:

            reply = "No services have been added yet."

    # -----------------------------------
    # LOCATION
    # -----------------------------------

    elif incoming_msg in [
        "3",
        "location",
        "address"
    ]:

        reply = f"📍 {business.location}"

    # -----------------------------------
    # OPENING HOURS
    # -----------------------------------

    elif incoming_msg in [
        "4",
        "hours",
        "opening hours"
    ]:

        reply = f"🕒 {business.opening_hours}"

    # -----------------------------------
    # AI RECEPTIONIST
    # -----------------------------------

    else:

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

Instructions:

{business.ai_prompt}

Rules:

- Only recommend services listed above.
- Never invent services.
- Never invent prices.
- Keep replies short.
- Be friendly and professional.
- Encourage customers to book appointments.

Customer Message:

{incoming_msg}
"""

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
