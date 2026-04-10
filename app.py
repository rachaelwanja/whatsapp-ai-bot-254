from flask import Flask, request, redirect, session
from twilio.twiml.messaging_response import MessagingResponse
import requests
import json
import os
import datetime

app = Flask(__name__)
app.secret_key = "flowai-secret"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ================= LOAD =================
def load_clients():
    try:
        with open("clients.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_clients(data):
    with open("clients.json", "w") as f:
        json.dump(data, f, indent=4)

clients = load_clients()

# ================= MEMORY =================
memory = {}
state = {}
user_client = {}

# ================= LEADS =================
try:
    with open("leads.json", "r") as f:
        leads = json.load(f)
except:
    leads = []

def save_leads():
    with open("leads.json", "w") as f:
        json.dump(leads, f, indent=4)

# ================= AI =================
def ask_ai(user, message, client):

    if user not in memory:
        memory[user] = []

    memory[user].append(message)
    memory[user] = memory[user][-5:]

    conversation = "\n".join(memory[user])

    prompt = f"""
You are a WhatsApp assistant for {client['name']}.

Keep replies short, friendly and helpful.

Business info:
Location: {client.get('location')}
Services: {", ".join(client.get("services", []))}
Fee: {client.get("consultation_fee")}
"""

    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": conversation}
                ]
            }
        )

        data = res.json()
        reply = data["choices"][0]["message"]["content"]

        memory[user].append(reply)
        return reply

    except:
        return "⚠️ AI error"

# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")

        # admin
        if u == "admin" and p == "1234":
            session["role"] = "admin"
            return redirect("/dashboard")

        # clients
        for key, c in clients.items():
            acc = c.get("account", {})
            if acc.get("username") == u and acc.get("password") == p:
                session["role"] = "client"
                session["client_key"] = key
                return redirect("/dashboard")

        return "Invalid login"

    return """
    <h2>Login</h2>
    <form method='POST'>
    <input name='username'><br><br>
    <input name='password' type='password'><br><br>
    <button>Login</button>
    </form>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ================= DASHBOARD =================
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if not session.get("role"):
        return redirect("/login")

    global clients

    # add client form
    if request.method == "POST" and session["role"] == "admin":

        name = request.form.get("name")
        phone = request.form.get("phone")
        location = request.form.get("location")

        key = f"whatsapp:{phone}"

        clients = load_clients()

        clients[key] = {
            "type": "hospital",
            "name": name,
            "location": location,
            "phone": phone,
            "services": ["Consultation", "Lab"],
            "consultation_fee": "KSh 1500",
            "account": {
                "username": name.lower().replace(" ", ""),
                "password": "1234"
            }
        }

        save_clients(clients)

    html = "<h1>FlowAI Dashboard</h1><hr>"

    # ADMIN VIEW
    if session["role"] == "admin":

        html += """
        <h3>Add Client</h3>
        <form method='POST'>
        <input name='name' placeholder='Name'><br>
        <input name='phone' placeholder='+254...'><br>
        <input name='location' placeholder='Location'><br>
        <button>Add</button>
        </form><hr>
        """

        html += "<h3>Clients</h3>"
        for c in clients.values():
            html += f"<p>{c['name']}</p>"

        html += "<h3>All Leads</h3>"
        for l in leads:
            html += f"<p>{l['client']} - {l.get('name')}</p>"

    # CLIENT VIEW
    else:
        key = session.get("client_key")
        client = clients.get(key)

        html += f"<h2>{client['name']}</h2>"

        html += "<h3>Your Leads</h3>"

        for l in leads:
            if l["client"] == client["name"]:
                html += f"<p>{l.get('name')} - {l.get('date')}</p>"

    html += "<br><a href='/logout'>Logout</a>"

    return html

# ================= WHATSAPP =================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    msg_in = request.values.get("Body", "").strip()
    lower = msg_in.lower()
    user = request.values.get("From")

    resp = MessagingResponse()
    msg = resp.message()

    # reset
    if lower in ["menu", "change"]:
        user_client.pop(user, None)
        msg.body("Type hi to start")
        return str(resp)

    # select business
    if user not in user_client:

        if lower in ["hi", "hello"]:
            msg.body("1 Hospital\n2 School\n3 Transport")
            return str(resp)

        elif lower == "1":
            client = next((c for c in clients.values() if c["type"] == "hospital"), None)
            user_client[user] = client
            msg.body(client["name"])
            return str(resp)

        else:
            msg.body("Type hi")
            return str(resp)

    client = user_client[user]

    # booking flow
    if state.get(user, {}).get("step") == "name":
        state[user] = {"step": "date", "name": msg_in}
        msg.body("Date?")
        return str(resp)

    elif state.get(user, {}).get("step") == "date":
        state[user]["date"] = msg_in
        state[user]["step"] = "service"
        msg.body("Service?")
        return str(resp)

    elif state.get(user, {}).get("step") == "service":

        leads.append({
            "user": user,
            "client": client["name"],
            "name": state[user]["name"],
            "date": state[user]["date"],
            "service": msg_in,
            "time": str(datetime.datetime.now())
        })

        save_leads()
        state[user] = {}

        msg.body("Booked!")
        return str(resp)

    # trigger booking
    if "book" in lower:
        state[user] = {"step": "name"}
        msg.body("Your name?")
        return str(resp)

    # AI reply
    reply = ask_ai(user, msg_in, client)
    msg.body(reply)

    return str(resp)

@app.route("/")
def home():
    return "FlowAI Running 🚀"

if __name__ == "__main__":
    app.run()
