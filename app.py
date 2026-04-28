from flask import Flask, request, render_template, redirect, session, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
import datetime, os, requests, base64

app = Flask(__name__)
app.secret_key = "secret"

# DATABASE
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
db = SQLAlchemy(app)

# CONFIG
PLANS = {"basic": 500, "pro": 1000, "premium": 2000}
user_sessions = {}

# MODELS
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    username = db.Column(db.String(50))
    password = db.Column(db.String(50))
    plan = db.Column(db.String(20), default="basic")
    active = db.Column(db.Boolean, default=True)
    expiry = db.Column(db.Date)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20))
    date = db.Column(db.String(100))
    client_id = db.Column(db.Integer)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20))
    amount = db.Column(db.Integer)
    date = db.Column(db.String(50))
    client_id = db.Column(db.Integer)

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():

    client_id = session.get("client_id")
    if not client_id:
        return redirect("/login")

    payments = Payment.query.filter_by(client_id=client_id).all()
    appointments = Appointment.query.filter_by(client_id=client_id).all()

    revenue = sum(p.amount or 0 for p in payments)

    chart_labels = [p.date for p in payments]
    chart_data = [p.amount or 0 for p in payments]

    return render_template(
        "dashboard.html",
        total_customers=len(appointments),
        total_bookings=len(appointments),
        revenue=revenue,
        payments=payments,
        chart_labels=chart_labels,
        chart_data=chart_data
    )

# ================= EXTRA PAGES =================
@app.route("/payments")
def payments_page():
    client_id = session.get("client_id")
    if not client_id:
        return redirect("/login")

    payments = Payment.query.filter_by(client_id=client_id).all()
    return render_template("payments.html", payments=payments)

@app.route("/customers")
def customers():
    client_id = session.get("client_id")
    if not client_id:
        return redirect("/login")

    customers = Appointment.query.filter_by(client_id=client_id).all()
    return render_template("customers.html", customers=customers)

@app.route("/settings")
def settings():
    client_id = session.get("client_id")
    if not client_id:
        return redirect("/login")

    client = Client.query.get(client_id)
    return render_template("settings.html", client=client)

# ================= AUTH =================
@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        client = Client(
            name=request.form["name"],
            phone=request.form["phone"],
            username=request.form["username"],
            password=request.form["password"],
            expiry=datetime.date.today() + datetime.timedelta(days=7)
        )
        db.session.add(client)
        db.session.commit()
        return redirect("/login")

    return render_template("signup.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        client = Client.query.filter_by(
            username=request.form["username"],
            password=request.form["password"]
        ).first()

        if client:
            session["client_id"] = client.id
            return redirect("/dashboard")

    return render_template("login.html")

# ================= HOME =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= INIT =================
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
