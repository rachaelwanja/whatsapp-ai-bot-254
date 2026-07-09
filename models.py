from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

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
    
class Service(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    business_id = db.Column(
        db.Integer
    )

    name = db.Column(
        db.String(200)
    )

    category = db.Column(
        db.String(100),
        default="General"
    )

    price = db.Column(
        db.Integer,
        default=0
    )

    duration = db.Column(
        db.String(100),
        default="30 mins"
    )

    deposit = db.Column(
        db.Integer,
        default=0
    )

    image = db.Column(
        db.String(500),
        default=""
    )

    available = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

class Payment(db.Model):

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

    amount = db.Column(
        db.Integer
    )

    mpesa_receipt = db.Column(
        db.String(100),
        default=""
    )

    status = db.Column(
        db.String(50),
        default="Pending"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

# =========================================
# CONVERSATIONS
# =========================================

class Conversation(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    business_id = db.Column(
        db.Integer,
        db.ForeignKey("business.id"),
        nullable=False
    )

    customer_phone = db.Column(
        db.String(30),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
