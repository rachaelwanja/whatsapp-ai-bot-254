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
