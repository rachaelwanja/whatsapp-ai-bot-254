from flask import Flask, request, render_template, redirect, session, Response, jsonify
import json, datetime

app = Flask(__name__)
app.secret_key = "super-secret-key"

# ================= LOAD / SAVE =================
def load_json(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

clients = load_json("clients.json")

# ================= PLANS =================
PLANS = {
    "basic": {"price": 500, "students": 50},
    "pro": {"price": 1000, "students": 200},
    "premium": {"price": 2000, "students": 9999}
}

# ================= SUPER ADMIN =================
SUPER_ADMIN = {"username": "admin", "password": "admin123"}

# ================= REGISTER STUDENT =================
def register_student(name, phone, client_key):

    client = clients[client_key]
    plan = client.get("plan", "basic")
    limit = PLANS[plan]["students"]

    data = load_json("students.json")
    if "students" not in data:
        data["students"] = []

    # count per client
    count = len([s for s in data["students"] if s.get("client") == client_key])

    if count >= limit:
        return False

    exists = any(s["phone"] == phone for s in data["students"])

    if not exists:
        data["students"].append({
            "name": name,
            "phone": phone,
            "client": client_key,
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

        for key, client in clients.items():
            acc = client.get("account", {})

            if acc.get("username") == username and acc.get("password") == password:
                session["client"] = key
                return redirect("/dashboard")

    return render_template("login.html")

# ================= DASHBOARD SWITCH =================
@app.route("/dashboard")
def dashboard():

    if "client" not in session:
        return redirect("/login")

    client = clients[session["client"]]

    # SCHOOL DASHBOARD
    if client.get("type") == "school":

        students = load_json("students.json").get("students", [])
        progress = load_json("progress.json").get("progress", [])

        students = [s for s in students if s.get("client") == session["client"]]

        return render_template(
            "school_dashboard.html",
            client=client,
            students=students,
            progress=progress
        )

    # CLINIC DASHBOARD
    appointments = load_json("appointments.json")
    data = [a for a in appointments if a["client"] == client["name"]]

    return render_template("dashboard.html", client=client, appointments=data)

# ================= WHATSAPP SCHOOL BOT =================
user_sessions = {}

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming = request.form.get("Body", "").strip()
    user = request.form.get("From")

    if user not in user_sessions:
        user_sessions[user] = {"step": "menu"}

    s = user_sessions[user]
    msg = incoming.lower()

    # MENU
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

    # QUIZ START
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

    # QUIZ ANSWER
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

    # HOMEWORK AI
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

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
