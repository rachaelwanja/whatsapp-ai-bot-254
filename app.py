from flask import Flask, request, render_template, redirect, session, Response, jsonify
import json, datetime

app = Flask(__name__)
app.secret_key = "super-secret-key"

# ================= FILE HANDLING =================
def load_json(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return [] if "appointments" in file else {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

clients = load_json("clients.json")

# ================= SESSION MEMORY (BOT) =================
user_sessions = {}

# ================= SAVE APPOINTMENT =================
def save_appointment(name, phone, date, slot, doctor, client_name):

    appointments = load_json("appointments.json")

    appointments.append({
        "id": str(datetime.datetime.now().timestamp()),
        "name": name,
        "phone": phone,
        "date": date,
        "slot": slot,
        "doctor": doctor,
        "client": client_name,
        "status": "pending",
        "created_at": str(datetime.datetime.now())
    })

    save_json("appointments.json", appointments)

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

# ================= DOCTOR LOGIN =================
@app.route("/doctor", methods=["GET", "POST"])
def doctor_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        for key, client in clients.items():
            for d in client.get("doctors", []):

                if d["username"] == username and d["password"] == password:

                    session["doctor"] = d["name"]
                    session["client"] = key

                    return redirect("/doctor/dashboard")

    return render_template("doctor_login.html")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():

    if "client" not in session:
        return redirect("/login")

    return render_template("dashboard.html", client=clients[session["client"]])

# ================= DOCTOR DASHBOARD =================
@app.route("/doctor/dashboard")
def doctor_dashboard():

    if "doctor" not in session:
        return redirect("/doctor")

    doctor = session["doctor"]
    client = clients[session["client"]]

    appointments = load_json("appointments.json")

    data = [
        a for a in appointments
        if a["doctor"] == doctor and a["client"] == client["name"]
    ]

    return render_template(
        "doctor_dashboard.html",
        appointments=data,
        doctor=doctor,
        client=client
    )

# ================= CALENDAR =================
@app.route("/calendar")
def calendar():

    if "client" not in session:
        return redirect("/login")

    client = clients[session["client"]]
    doctor_filter = request.args.get("doctor")

    appointments = load_json("appointments.json")

    data = [a for a in appointments if a["client"] == client["name"]]

    if doctor_filter:
        data = [a for a in data if a["doctor"] == doctor_filter]

    return render_template(
        "calendar.html",
        appointments=data,
        client=client,
        doctors=[d["name"] for d in client.get("doctors", [])],
        selected_doctor=doctor_filter
    )

# ================= APPROVE / REJECT =================
@app.route("/appointment_action", methods=["POST"])
def appointment_action():

    data = request.json
    appointment_id = data.get("id")
    action = data.get("action")

    appointments = load_json("appointments.json")

    for a in appointments:
        if a["id"] == appointment_id:
            a["status"] = action

    save_json("appointments.json", appointments)

    return jsonify({"status": "updated"})

# ================= DRAG RESCHEDULE =================
@app.route("/reschedule_drag", methods=["POST"])
def reschedule_drag():

    data = request.json
    appointment_id = data.get("id")
    new_date = data.get("date")
    new_slot = data.get("slot")

    appointments = load_json("appointments.json")

    for a in appointments:
        if a["id"] == appointment_id:
            a["date"] = new_date
            a["slot"] = new_slot

    save_json("appointments.json", appointments)

    return jsonify({"status": "updated"})

# ================= PATIENT HISTORY =================
@app.route("/patient_history", methods=["POST"])
def patient_history():

    data = request.json
    phone = data.get("phone")
    client_name = data.get("client")

    appointments = load_json("appointments.json")

    history = [
        a for a in appointments
        if a["phone"] == phone and a["client"] == client_name
    ]

    return jsonify({"history": history})

# ================= WHATSAPP (CONVERSATIONAL BOT 🇰🇪) =================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming = request.form.get("Body", "").strip()
    user = request.form.get("From")

    if user not in user_sessions:
        user_sessions[user] = {"step": "start"}

    s = user_sessions[user]

    # STEP 1: GREETING
    if s["step"] == "start":
        s["step"] = "menu"

        return Response("""
<Response>
<Message>
Hello 👋 Welcome to CarePlus Clinic.

How may we assist you today?

1️⃣ Book appointment  
2️⃣ Check available slots  
3️⃣ Talk to support
</Message>
</Response>
""", mimetype="text/xml")

    # STEP 2: MENU
    elif s["step"] == "menu":

        if incoming == "1":
            s["step"] = "name"

            return Response("""
<Response>
<Message>
Great 👍 Kindly share your full name.
</Message>
</Response>
""", mimetype="text/xml")

        return Response("""
<Response>
<Message>
Please reply with 1, 2 or 3.
</Message>
</Response>
""", mimetype="text/xml")

    # STEP 3: NAME
    elif s["step"] == "name":

        s["name"] = incoming
        s["step"] = "date"

        return Response(f"""
<Response>
<Message>
Thank you {incoming} 😊

Please provide your preferred date (e.g. 2026-05-01).
</Message>
</Response>
""", mimetype="text/xml")

    # STEP 4: DATE
    elif s["step"] == "date":

        s["date"] = incoming
        s["step"] = "slot"

        return Response("""
<Response>
<Message>
Select your preferred time:

1️⃣ Morning  
2️⃣ Afternoon
</Message>
</Response>
""", mimetype="text/xml")

    # STEP 5: SLOT
    elif s["step"] == "slot":

        slot = "morning" if incoming == "1" else "afternoon"
        s["slot"] = slot
        s["step"] = "doctor"

        return Response("""
<Response>
<Message>
Select your doctor:

1️⃣ Dr. Kamau  
2️⃣ Dr. Achieng
</Message>
</Response>
""", mimetype="text/xml")

    # STEP 6: DOCTOR
    elif s["step"] == "doctor":

        doctor = "Dr. Kamau" if incoming == "1" else "Dr. Achieng"

        save_appointment(
            s["name"],
            user,
            s["date"],
            s["slot"],
            doctor,
            list(clients.values())[0]["name"]
        )

        user_sessions[user] = {"step": "start"}

        return Response(f"""
<Response>
<Message>
Thank you {s['name']} 🙏

Your appointment has been successfully scheduled:

📅 Date: {s['date']}  
⏰ Time: {s['slot'].capitalize()}  
👨‍⚕️ Doctor: {doctor}  

We look forward to serving you.
</Message>
</Response>
""", mimetype="text/xml")

    return Response("<Response><Message>OK</Message></Response>", mimetype="text/xml")

# ================= HOME =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
