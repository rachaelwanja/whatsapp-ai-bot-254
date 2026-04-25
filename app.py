from flask import Flask, request, render_template, redirect, session, Response, jsonify
import json, datetime, os
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "super-secret-key"

# ================= DATABASE =================
uri = os.getenv("DATABASE_URL")

if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= MODELS =================
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    type = db.Column(db.String(50))
    plan = db.Column(db.String(20))
    active = db.Column(db.Boolean, default=True)
    expiry = db.Column(db.Date)
    phone = db.Column(db.String(20))
    username = db.Column(db.String(50))
    password = db.Column(db.String(50))

# ================= DEBUG ROUTES =================
@app.route("/routes")
def routes():
    return str(app.url_map)

@app.route("/test")
def test():
    return "TEST WORKING"

# ================= LOAD / SAVE (TEMP) =================
def load_json(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ================= PLANS =================
PLANS = {
    "basic": {"price": 500, "students": 50},
    "pro": {"price": 1000, "students": 200},
    "premium": {"price": 2000, "students": 9999}
}

# ================= SUPER ADMIN =================
SUPER_ADMIN = {"username": "admin", "password": "admin123"}

# ================= REGISTER STUDENT =================
def register_student(name, phone, client_id):
    client = Client.query.get(client_id)
    plan = client.plan or "basic"
    limit = PLANS[plan]["students"]

    data = load_json("students.json")
    if "students" not in data:
        data["students"] = []

    count = len([s for s in data["students"] if s.get("client") == client_id])

    if count >= limit:
        return False

    exists = any(s["phone"] == phone for s in data["students"])

    if not exists:
        data["students"].append({
            "name": name,
            "phone": phone,
            "client": client_id,
            "joined": str(datetime.datetime.now())
        })

    save_json("students.json", data)
    return True

# ================= SAVE PROGRESS =================
def save_progress(phone, subject, score):
    data = load_json("progress.json")
    if "progress" not in data:
        data["progress"] = []

    data["progress"].append({
        "phone": phone,
        "subject": subject,
        "score": score,
        "date": str(datetime.datetime.now())
    })

    save_json("progress.json", data)

# ================= LOGIN =================
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

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():

    if "client_id" not in session:
        return redirect("/login")

    client = Client.query.get(session["client_id"])

    if not client or not client.active:
        return render_template("expired.html")

    # SCHOOL DASHBOARD
    if client.type == "school":

        students = load_json("students.json").get("students", [])
        progress = load_json("progress.json").get("progress", [])

        students = [s for s in students if s.get("client") == client.id]

        return render_template(
            "school_dashboard.html",
            client=client,
            students=students,
            progress=progress
        )

    # CLINIC DASHBOARD
    appointments = load_json("appointments.json")
    data = [a for a in appointments if a["client"] == client.name]

    return render_template("dashboard.html", client=client, appointments=data)

# ================= WHATSAPP BOT =================
user_sessions = {}

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming = request.form.get("Body", "").strip()
    user = request.form.get("From")

    if user not in user_sessions:
        user_sessions[user] = {"step": "menu"}

    s = user_sessions[user]
    msg = incoming.lower()

    if msg in ["hi", "menu", "hey", "hello"]:
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
        save_progress(user, "math", score)

        s["step"] = "menu"

        return Response("""
<Response>
<Message>
Answer recorded ✅
</Message>
</Response>
""", mimetype="text/xml")

    if "solve" in msg or any(c.isdigit() for c in msg):
        return Response(f"""
<Response>
<Message>
Let's solve it step-by-step 😊

(Connect OpenAI here for full AI)
</Message>
</Response>
""", mimetype="text/xml")

    return Response("<Response><Message>Type menu</Message></Response>", mimetype="text/xml")

# ================= SUPER ADMIN =================
@app.route("/superadmin", methods=["GET", "POST"])
def superadmin():

    if request.method == "POST":
        if request.form["username"] == SUPER_ADMIN["username"] and \
           request.form["password"] == SUPER_ADMIN["password"]:

            session["admin"] = True
            return redirect("/superadmin/dashboard")

    return render_template("superadmin_login.html")

@app.route("/superadmin/dashboard")
def admin_dashboard():

    if not session.get("admin"):
        return redirect("/superadmin")

    students = load_json("students.json").get("students", [])
    payments = load_json("payments.json").get("payments", [])

    revenue = sum(p["amount"] for p in payments)

    clients = Client.query.all()

    return render_template(
        "superadmin_dashboard.html",
        clients=clients,
        total_clients=len(clients),
        total_students=len(students),
        revenue=revenue
    )

# ================= HOME =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= INIT DB =================
with app.app_context():
    db.create_all()

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
