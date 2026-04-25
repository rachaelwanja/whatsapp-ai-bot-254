from flask import Flask, request, render_template, redirect, session, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
import datetime, os

app = Flask(__name__)
app.secret_key = "super-secret-key"

# ================= DATABASE =================
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= MODELS =================
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    type = db.Column(db.String(50))  # school, clinic, salon, etc
    phone = db.Column(db.String(20))
    username = db.Column(db.String(50))
    password = db.Column(db.String(50))
    plan = db.Column(db.String(20), default="basic")

    active = db.Column(db.Boolean, default=False)
    expiry = db.Column(db.Date)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    client_id = db.Column(db.Integer)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20))
    subject = db.Column(db.String(50))
    score = db.Column(db.Integer)
    client_id = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    client_id = db.Column(db.Integer)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    date = db.Column(db.String(50))
    client_id = db.Column(db.Integer)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20))
    amount = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    client_id = db.Column(db.Integer)

# ================= INIT DB =================
with app.app_context():
    db.create_all()

# ================= PLANS =================
PLANS = {
    "basic": {"price": 500, "students": 50},
    "pro": {"price": 1000, "students": 200},
    "premium": {"price": 2000, "students": 9999}
}

# ================= AUTH =================
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        client = Client(
            name=request.form["name"],
            phone=request.form["phone"],
            username=request.form["username"],
            password=request.form["password"],
            type=request.form["type"],
            plan="basic",
            active=False
        )

        db.session.add(client)
        db.session.commit()

        return redirect("/login")

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        client = Client.query.filter_by(username=username, password=password).first()

        if client:
            session["client_id"] = client.id
            return redirect("/dashboard")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():

    if "client_id" not in session:
        return redirect("/login")

    client = Client.query.get(session["client_id"])

    # 🔥 SUBSCRIPTION CHECK
    if not client.active or not client.expiry or client.expiry < datetime.date.today():
        return render_template("expired.html", client=client)

    # BUSINESS ROUTING
    if client.type == "school":
        students = Student.query.filter_by(client_id=client.id).all()
        progress = Progress.query.filter_by(client_id=client.id).all()

        total_students = len(students)
        total_quizzes = len(progress)

        return render_template(
            "school_dashboard.html",
            client=client,
            students=students,
            progress=progress,
            total_students=total_students,
            total_quizzes=total_quizzes
        )

    if client.type == "clinic":
        appointments = Appointment.query.filter_by(client_id=client.id).all()
        patients = Patient.query.filter_by(client_id=client.id).all()

        return render_template(
            "appointments.html",
            client=client,
            appointments=appointments,
            patients=patients
        )

    return render_template("dashboard.html", client=client)

# ================= BILLING =================
@app.route("/billing")
def billing():

    if "client_id" not in session:
        return redirect("/login")

    client = Client.query.get(session["client_id"])
    payments = Payment.query.filter_by(client_id=client.id).all()

    return render_template("billing.html", client=client, payments=payments)

# ================= MPESA CALLBACK =================
@app.route("/mpesa/callback", methods=["POST"])
def mpesa_callback():

    data = request.json

    phone = data.get("phone")
    amount = data.get("amount")

    client = Client.query.filter_by(phone=phone).first()

    if client:

        # SAVE PAYMENT
        payment = Payment(
            phone=phone,
            amount=amount,
            client_id=client.id
        )

        db.session.add(payment)

        # ACTIVATE SUBSCRIPTION
        client.active = True
        client.expiry = datetime.date.today() + datetime.timedelta(days=30)

        db.session.commit()

    return jsonify({"status": "ok"})

# ================= WHATSAPP BOT =================
user_sessions = {}

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming = request.form.get("Body", "").strip()
    user = request.form.get("From")

    # 🔥 TEMP CLIENT (later map per number)
    client = Client.query.first()

    # 🔒 BLOCK IF NOT PAID
    if not client.active or not client.expiry or client.expiry < datetime.date.today():
        return Response("""
<Response>
<Message>
⚠️ Subscription expired.
Please pay to continue.
</Message>
</Response>
""", mimetype="text/xml")

    msg = incoming.lower()

    if user not in user_sessions:
        user_sessions[user] = {"step": "menu"}

    s = user_sessions[user]

    # ================= SCHOOL BOT =================
    if client.type == "school":

        if msg in ["hi", "menu"]:
            return Response("""
<Response>
<Message>
Welcome 📚

1️⃣ Homework help
2️⃣ Take a quiz
</Message>
</Response>
""", mimetype="text/xml")

        if msg == "2":
            s["step"] = "quiz"
            return Response("""
<Response>
<Message>
What is 8 × 7?

A) 54
B) 56
C) 64
</Message>
</Response>
""", mimetype="text/xml")

        if s.get("step") == "quiz":

            score = 1 if msg.upper() == "B" else 0

            progress = Progress(
                phone=user,
                subject="math",
                score=score,
                client_id=client.id
            )

            db.session.add(progress)
            db.session.commit()

            s["step"] = "menu"

            return Response("""
<Response>
<Message>
Answer recorded ✅
</Message>
</Response>
""", mimetype="text/xml")

    # ================= CLINIC BOT =================
    if client.type == "clinic":

        if msg in ["hi", "menu"]:
            return Response("""
<Response>
<Message>
Welcome 🏥

1️⃣ Book Appointment
</Message>
</Response>
""", mimetype="text/xml")

        if msg == "1":
            appointment = Appointment(
                name=user,
                phone=user,
                date=str(datetime.datetime.now()),
                client_id=client.id
            )

            db.session.add(appointment)
            db.session.commit()

            return Response("""
<Response>
<Message>
Appointment booked ✅
</Message>
</Response>
""", mimetype="text/xml")

    return Response("<Response><Message>Type menu</Message></Response>", mimetype="text/xml")

# ================= HOME =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
