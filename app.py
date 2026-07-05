from flask import Flask, render_template, request, redirect, session, flash, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from twilio.twiml.voice_response import VoiceResponse
from twilio.twiml.messaging_response import MessagingResponse
import os
import uuid

from werkzeug.utils import secure_filename
import requests
import base64
from models import db, Business, Appointment, Service, Payment
from services import (
    get_access_token,
    generate_password,
    stk_push,
    ask_ai
)
app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = "static/uploads"

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

db.init_app(app)
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
        print("SIGNUP USERNAME:", username)
        print("EXISTING USER:", existing_user)

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
        
@app.route("/services")
def services():

    if "business_id" not in session:
        return redirect("/login")

    business_id = session["business_id"]

    business = Business.query.get(business_id)

    services = Service.query.filter_by(
        business_id=business_id
    ).all()

    return render_template(
        "services.html",
        business=business,
        services=services
    )
    
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
    
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        business = Business.query.filter_by(
            username=username
        ).first()

        print("USERNAME:", username)
        print("BUSINESS:", business)
        print("ENTERED PASSWORD:", password)

        if business:
            print("STORED HASH:", business.password)
            print(
                "PASSWORD MATCH:",
                check_password_hash(
                    business.password,
                    password
                )
            )

        if business and check_password_hash(
            business.password,
            password
        ):

            session["business_id"] = business.id

            return redirect("/dashboard")

        flash("Invalid credentials")

        return redirect("/login")

    return render_template("login.html")
    
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

    payments = Payment.query.filter_by(
        business_id=business_id
    ).order_by(
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

    # Get the business
    business = Business.query.first()

    if not business:

        twiml = """
<Response>
    <Message>No business has been configured yet.</Message>
</Response>
"""

        return Response(
            twiml,
            mimetype="text/xml"
        )

    # -------------------------------
    # MAIN MENU
    # -------------------------------

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

    # -------------------------------
    # BOOK APPOINTMENT
    # -------------------------------

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

    # -------------------------------
    # SERVICES
    # -------------------------------

    elif incoming_msg in [
        "2",
        "prices",
        "services"
    ]:

        services = Service.query.filter_by(
            business_id=business.id
        ).all()

        if services:

            reply = "Our Services:\n\n"

            for service in services:

                reply += (
                    f"• {service.name} - "
                    f"KES {service.price}\n"
                )

        else:

            reply = "No services have been added yet."

    # -------------------------------
    # LOCATION
    # -------------------------------

    elif incoming_msg in [
        "3",
        "location",
        "address"
    ]:

        reply = f"""
📍 {business.location}
"""

    # -------------------------------
    # OPENING HOURS
    # -------------------------------

    elif incoming_msg in [
        "4",
        "hours",
        "opening hours"
    ]:

        reply = f"""
🕒 {business.opening_hours}
"""

    # -------------------------------
    # AI RECEPTIONIST
    # -------------------------------

    else:

        services = Service.query.filter_by(
            business_id=business.id
        ).all()

        services_text = ""

        if services:

            for service in services:

                services_text += (
                    f"- {service.name}: "
                    f"KES {service.price} "
                    f"({service.duration})\n"
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
- If you don't know something, politely say so.
- Keep replies friendly, professional, and concise.
- Encourage customers to book an appointment when appropriate.

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
