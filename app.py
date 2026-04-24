from flask import Flask, request, jsonify, render_template, redirect, session, Response
import requests, json, os, datetime
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "flowai-secret"

# ================= CONFIG =================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MPESA_API_URL = "https://whatsapp-ai-bot-254-1.onrender.com/stk"

# ================= FILE =================
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
users = load_json("users.json")
memory = {}

# ================= FEATURES =================
def has_feature(client, feature):
    tier = client.get("tier", "basic")

    features = {
        "basic": ["ai"],
        "pro": ["ai", "analytics", "booking"],
        "premium": ["ai", "analytics", "booking", "priority"]
    }

    return feature in features.get(tier, [])

# ================= AI =================
def ask_ai(user, message, client):

    memory.setdefault(user, [])
    memory[user].append(message)
    memory[user] = memory[user][-5:]

    prompt = f"""
You are assistant for {client['name']}.
Be friendly and helpful.
"""

    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "\n".join(memory[user])}
                ]
            }
        )

        return res.json()["choices"][0]["message"]["content"]

    except:
        return "⚠️ AI error"

# ================= PLAN =================
def is_active(client):
    if client.get("plan") == "paid":
        return True

    expiry = client.get("expiry")

    if not expiry:
        return False

    try:
        expiry_date = datetime.datetime.fromisoformat(expiry)
        return datetime.datetime.now() < expiry_date
    except:
        return False

def get_days_left(client):
    expiry = client.get("expiry")

    if not expiry:
        return 0

    try:
        expiry_date = datetime.datetime.fromisoformat(expiry)
        remaining = expiry_date - datetime.datetime.now()
        return max(0, remaining.days)
    except:
        return 0

# ================= LEADS =================
def save_lead(phone, message, client_id):

    client = clients.get(client_id)

    is_booking = False
    if client and has_feature(client, "booking"):
        is_booking = "book" in message.lower()

    lead = {
        "phone": phone,
        "message": message,
        "client": client_id,
        "time": str(datetime.datetime.now()),
        "booked": is_booking
    }

    leads = load_json("leads.json")
    if not isinstance(leads, list):
        leads = []

    leads.append(lead)
    save_json("leads.json", leads)

# ================= ANALYTICS =================
def get_analytics(client_id):

    leads = load_json("leads.json")
    payments = load_json("payments.json")

    leads = leads if isinstance(leads, list) else []
    payments = payments if isinstance(payments, list) else []

    total_leads = len([l for l in leads if l["client"] == client_id])
    total_bookings = len([l for l in leads if l["client"] == client_id and l["booked"]])
    total_payments = len([p for p in payments if p["status"] == "SUCCESS"])

    conversion = (total_payments / total_leads * 100) if total_leads else 0

    return {
        "leads": total_leads,
        "bookings": total_bookings,
        "payments": total_payments,
        "conversion": round(conversion, 2)
    }

# ================= MPESA =================
def stk_push(phone, amount):
    try:
        requests.post(MPESA_API_URL, json={"phone": phone, "amount": amount})
    except:
        pass

# ================= AUTH =================
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        u = request.form.get("username")
        p = request.form.get("password")
        name = request.form.get("name")
        phone = request.form.get("phone")

        clients[u] = {
            "name": name,
            "phone": phone,
            "keyword": u,
            "account": {"username": u, "password": p},
            "tier": "basic",
            "plan": "trial",
            "expiry": str(datetime.datetime.now() + timedelta(days=3))
        }

        save_json("clients.json", clients)
        return redirect("/login")

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")

        for k, c in clients.items():
            if c["account"]["username"] == u and c["account"]["password"] == p:
                session["client"] = k
                return redirect("/dashboard")

    return render_template("login.html")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():

    if "client" not in session:
        return redirect("/login")

    client_id = session["client"]
    client = clients[client_id]

    status = "ACTIVE ✅" if is_active(client) else "EXPIRED ❌"
    days_left = get_days_left(client)

    if has_feature(client, "analytics"):
        analytics = get_analytics(client_id)
    else:
        analytics = {"leads": 0, "bookings": 0, "payments": 0, "conversion": 0}

    return render_template(
        "dashboard.html",
        client=client,
        status=status,
        expiry=client.get("expiry"),
        days_left=days_left,
        analytics=analytics
    )

# ================= PAY =================
@app.route("/pay", methods=["POST"])
def pay():

    client = clients[session["client"]]
    stk_push(client["phone"], 1000)

    return jsonify({"message": "📲 Payment sent"})

# ================= ACTIVATE =================
@app.route("/activate", methods=["POST"])
def activate():

    phone = request.json.get("phone")

    for k, c in clients.items():
        if c["phone"] == phone:
            c["plan"] = "paid"
            c["expiry"] = str(datetime.datetime.now() + timedelta(days=30))

    save_json("clients.json", clients)
    return {"status": "ok"}

# ================= WHATSAPP =================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming = request.form.get("Body").lower()
    phone = request.form.get("From").replace("whatsapp:", "").replace("+", "")

    # SWITCH
    if incoming.startswith("switch"):
        key = incoming.split()[1]
        if key in clients:
            users[phone] = key
            save_json("users.json", users)
            return Response(f"<Response><Message>Switched to {key}</Message></Response>", mimetype="text/xml")

    client_id = users.get(phone)

    if not client_id:
        client_id = list(clients.keys())[0]
        users[phone] = client_id
        save_json("users.json", users)

    client = clients[client_id]

    save_lead(phone, incoming, client_id)

    if not is_active(client):
        stk_push(client["phone"], 1000)
        reply = "⚠️ Subscription expired"
    else:
        reply = ask_ai(phone, incoming, client)

    return Response(f"<Response><Message>{reply}</Message></Response>", mimetype="text/xml")

# ================= HOME =================
@app.route("/")
def home():
    return "🚀 FlowAI LIVE"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
