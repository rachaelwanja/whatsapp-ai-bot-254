from flask import Flask, request, render_template, redirect, session, Response
import datetime, os, json

from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key")

# ================= DATABASE =================
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= MODEL =================
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

    # create default test user
    if not Client.query.first():
        demo = Client(
            name="Demo School",
            type="school",
            plan="pro",
            active=True,
            phone="254700000000",
            username="school1",
            password="1234"
        )
        db.session.add(demo)
        db.session.commit()

# ================= JSON HELPERS =================
def load_json(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ================= HOME =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= SIGNUP =================
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        username = request.form.get("username")
        password = request.form.get("password")

        print("SIGNUP:", username)

        # check existing
        if Client.query.filter_by(username=username).first():
            return "Username already exists ❌"

        new_user = Client(
            name=name,
            phone=phone,
            username=username,
            password=password,
            type="school",
            plan="basic",
            active=True,
            expiry=datetime.date.today() + datetime.timedelta(days=30)
        )

        db.session.add(new_user)
        db.session.commit()

        print("USER CREATED:", username)

        return redirect("/login")

    return render_template("signup.html")

# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        print("LOGIN ATTEMPT:", username, password)

        client = Client.query.filter_by(username=username).first()

        if client:
            print("FOUND USER:", client.username, client.password)

            if client.password == password:
                session["client_id"] = client.id
                print("LOGIN SUCCESS")
                return redirect("/dashboard")

        print("LOGIN FAILED")
        return "Invalid login ❌"

    return render_template("login.html")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():

    if "client_id" not in session:
        return redirect("/login")

    client = Client.query.get(session["client_id"])

    if not client:
        return redirect("/login")

    if not client.active:
        return render_template("expired.html")

    students = load_json("students.json").get("students", [])
    students = [s for s in students if s.get("client") == client.id]

    return render_template(
        "school_dashboard.html",
        client=client,
        students=students
    )

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

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
</Message>
</Response>
""", mimetype="text/xml")

    return Response("<Response><Message>Type menu</Message></Response>", mimetype="text/xml")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
