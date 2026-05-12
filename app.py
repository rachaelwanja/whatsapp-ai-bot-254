from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from datetime import datetime
import os
import requests

app = Flask(__name__)

# ====================================
# CONFIG
# ====================================

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "flowai-secret"
)

database_url = os.environ.get("DATABASE_URL")

# Render sometimes gives postgres://
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ====================================
# DATABASE MODEL
# ====================================

class Business(db.Model):

    __tablename__ = "business"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(200),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(500),
        nullable=False
    )

    business_name = db.Column(
        db.String(200)
    )

    business_phone = db.Column(
        db.String(100)
    )

    plan = db.Column(
        db.String(50),
        default="free"
    )

    opening_time = db.Column(
        db.String(50),
        default="08:00"
    )

    closing_time = db.Column(
        db.String(50),
        default="17:00"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

# ====================================
# HOME
# ====================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )

# ====================================
# SIGNUP
# ====================================

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

# ====================================
# LOGIN
# ====================================

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

        if business:

            password_correct = check_password_hash(
                business.password,
                password
            )

            if password_correct:

                session["business_id"] = business.id

                return redirect(
                    "/dashboard"
                )

        flash(
            "Invalid username or password"
        )

        return redirect(
            "/login"
        )

    return render_template(
        "login.html"
    )

# ====================================
# DASHBOARD
# ====================================

@app.route("/dashboard")
def dashboard():

    if "business_id" not in session:

        return redirect(
            "/login"
        )

    business = Business.query.get(
        session["business_id"]
    )

    if not business:

        session.clear()

        return redirect(
            "/login"
        )

    return render_template(
        "dashboard.html",
        business=business
    )

# ====================================
# LOGOUT
# ====================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        "/login"
    )

# ====================================
# RESET DATABASE
# ====================================

@app.route("/reset-database")
def reset_database():

    try:

        db.session.execute(
            text("DROP SCHEMA public CASCADE")
        )

        db.session.execute(
            text("CREATE SCHEMA public")
        )

        db.session.commit()

        db.create_all()

        return "✅ DATABASE RESET SUCCESSFUL"

    except Exception as e:

        db.session.rollback()

        return f"ERROR: {str(e)}"

# ====================================
# ELEVENLABS TEST
# ====================================

@app.route("/voice-test")
def voice_test():

    api_key = os.environ.get(
        "ELEVENLABS_API_KEY"
    )

    voice_id = os.environ.get(
        "ELEVENLABS_VOICE_ID"
    )

    if not api_key or not voice_id:

        return "Missing ElevenLabs environment variables"

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {

        "xi-api-key": api_key,

        "Content-Type": "application/json"

    }

    data = {

        "text": "Habari. Karibu FlowAI. Ninaweza kusaidia biashara yako.",

        "model_id": "eleven_multilingual_v2"

    }

    response = requests.post(

        url,

        json=data,

        headers=headers

    )

    return f"""

    <h2>Voice Test</h2>

    <p>Status Code: {response.status_code}</p>

    <pre>{response.text}</pre>

    """

# ====================================
# CREATE TABLES
# ====================================

with app.app_context():

    db.create_all()

# ====================================
# RUN APP
# ====================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
