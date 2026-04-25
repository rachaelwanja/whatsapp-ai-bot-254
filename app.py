from flask import Flask, request, render_template, redirect, session, Response
import datetime, os, json

from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key")

# ================= DATABASE =================
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
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
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))

# ================= INIT DB =================
with app.app_context():
    db.create_all()

    # Create default user if DB empty
    if not Client.query.first():
        demo = Client(
            name="Bright Future Academy",
            type="school",
            plan="pro",
            active=True,
            phone="254700000002",
            username="school1",
            password="1234"
        )
        db.session.add(demo)
        db.session.commit()

# ================= TEMP JSON (FOR STUDENTS ONLY) =================
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

# ================= SIGNUP =================
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        username = request.form["username"]
        password = request.form["password"]

        # check existing user
        if Client.query.filter_by(username=username).first():
            return "Username already exists"

        new_client = Client(
            name=name,
            phone=phone,
            username=username,
            password=password,
            type="school",
            plan="basic",
            active=True,
            expiry=datetime.date.today() + datetime.timedelta(days=30)
        )

        db.session.add(new_client)
        db.session.commit()

        return redirect("/login")

    return render_template("signup.html")

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

    if not client.active:
        return render_template("expired.html")

    students = load_json("students.json").get("students", [])
    students = [s for s in students if s.get("client") == client.id]

    return render_template(
        "school_dashboard.html",
        client=client,
        students=students
    )

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

    data["students"].append({
        "name": name,
        "phone": phone,
        "client": client_id,
        "joined": str(datetime.datetime.now())
    })

    save_json("students.json", data)
    return True

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

        data = load_json("progress.json")
        if "progress" not in data:
            data["progress"] = []

        data["progress"].append({
            "phone": user,
            "subject": "math",
            "score": score,
            "date": str(datetime.datetime.now())
        })

        save_json("progress.json", data)

        s["step"] = "menu"

        return Response("""
<Response>
<Message>
Answer recorded ✅
</Message>
</Response>
""", mimetype="text/xml")

    if "solve" in msg or any(c.isdigit() for c in msg):
        return Response("""
<Response>
<Message>
Let's solve it step-by-step 😊

(Connect OpenAI here for full AI)
</Message>
</Response>
""", mimetype="text/xml")

    return Response("<Response><Message>Type menu</Message></Response>", mimetype="text/xml")

# ================= HOME =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
