from flask import Flask, request, render_template, redirect, session, Response, jsonify
import json, datetime, os

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

# ================= APPOINTMENTS =================
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

# ================= AUTH =================
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        for key, client in clients.items():
            if client["account"]["username"] == request.form["username"]:
                session["client"] = key
                return redirect("/dashboard")

    return render_template("login.html")

# ================= DOCTOR LOGIN =================
@app.route("/doctor", methods=["GET","POST"])
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

    client = clients[session["client"]]

    return render_template("dashboard.html", client=client)

# ================= DOCTOR DASHBOARD =================
@app.route("/doctor/dashboard")
def doctor_dashboard():

    if "doctor" not in session:
        return redirect("/doctor")

    doctor_name = session["doctor"]
    client = clients[session["client"]]

    appointments = load_json("appointments.json")

    data = [
        a for a in appointments
        if a["doctor"] == doctor_name and a["client"] == client["name"]
    ]

    return render_template(
        "doctor_dashboard.html",
        appointments=data,
        doctor=doctor_name,
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

    data = [
        a for a in appointments
        if a["client"] == client["name"]
    ]

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

# ================= WHATSAPP BOT =================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming = request.form.get("Body", "")
    from_number = request.form.get("From")

    # prompt
    if "appointment" in incoming.lower():
        return Response("""
<Response>
<Message>
Send: Name Date Slot Doctor

Example:
John Doe 2026-05-01 morning Dr. Smith
</Message>
</Response>
""", mimetype="text/xml")

    try:
        parts = incoming.split()

        name = " ".join(parts[:-3])
        date = parts[-3]
        slot = parts[-2]
        doctor = parts[-1]

        save_appointment(name, from_number, date, slot, doctor, "CarePlus Clinic")

        return Response(f"""
<Response>
<Message>
Appointment booked for {date} ({slot}) with {doctor}.
</Message>
</Response>
""", mimetype="text/xml")

    except:
        return Response("<Response><Message>OK</Message></Response>")

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
