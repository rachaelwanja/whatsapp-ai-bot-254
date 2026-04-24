from flask import Flask, request, jsonify, render_template, redirect, session, Response
import requests, json, os, datetime
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "flowai-secret"

# ================= CONFIG =================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# 👉 Your external MPESA API
MPESA_API_URL = "https://whatsapp-ai-bot-254-1.onrender.com/stk"

# ================= PRICING =================
PRICES = {
    "basic": 500,
    "pro": 1000,
    "premium": 2000
}

# ================= FILE HANDLING =================
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
memory = {}

# ================= AI =================
def ask_ai(user, message, client):

    memory.setdefault(user, [])
    memory[user].append(message)
    memory[user] = memory[user][-5:]

    prompt = f"""
You are assistant for {client['name']}.
Services: {", ".join(client.get("services", []))}
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

    except Exception as e:
        print("AI ERROR:", str(e))
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

# ================= LEADS =================
def save_lead(phone, message, client_id):

    lead = {
        "phone": phone,
        "message": message,
        "client": client_id,
        "time": str(datetime.datetime.now()),
        "booked": "book" in message.lower()
    }

    leads = load_json("leads.json")
    if not isinstance(leads, list):
        leads = []

    leads.append(lead)
    save_json("leads.json", leads)

# ================= MPESA =================
def stk_push(phone, amount):

    payload = {
        "phone": phone,
        "amount": amount
    }

    try:
        res = requests.post(MPESA_API_URL, json=payload)
        print("💰 STK RESPONSE:", res.text)
    except Exception as e:
        print("❌ STK ERROR:", str(e))

# ================= AUTH =================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        u = request.form.get("username")
        p = request.form.get("password")

        if u == "admin" and p == "admin123":
            session["admin"] = True
            return redirect("/admin")

        for k, c in clients.items():
            if c["account"]["username"] == u and c["account"]["password"] == p:
                session["client"] = k
                return redirect("/dashboard")

    return render_template("login.html")

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
            "services": ["Customer Support"],
            "keyword": u,
            "account": {"username": u, "password": p},
            "plan": "trial",
            "tier": "basic",
            "expiry": str(datetime.datetime.now() + timedelta(days=3))
        }

        save_json("clients.json", clients)
        return redirect("/login")

    return render_template("signup.html")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():

    if "client" not in session:
        return redirect("/login")

    client_id = session["client"]
    client = clients[client_id]

    status = "ACTIVE ✅" if is_active(client) else "EXPIRED ❌"
    expiry = client.get("expiry", "N/A")

    return render_template(
        "dashboard.html",
        client=client,
        status=status,
        expiry=expiry
    )

# ================= SET PLAN =================
@app.route("/set_plan", methods=["POST"])
def set_plan():

    if "client" not in session:
        return jsonify({"message": "Not logged in"})

    data = request.json
    plan = data.get("plan")

    client_id = session["client"]
    clients[client_id]["tier"] = plan

    save_json("clients.json", clients)

    return jsonify({
        "message": f"✅ Plan set to {plan.upper()}"
    })

# ================= PAY =================
@app.route("/pay", methods=["POST"])
def pay():

    if "client" not in session:
        return jsonify({"message": "Not logged in"})

    client_id = session["client"]
    client = clients[client_id]

    tier = client.get("tier", "basic")
    amount = PRICES.get(tier, 1000)

    phone = client["phone"]

    stk_push(phone, amount)

    return jsonify({
        "message": f"📲 STK sent for KES {amount}"
    })

# ================= CHAT =================
@app.route("/chat_api", methods=["POST"])
def chat_api():

    data = request.json
    msg = data.get("message")
    client_id = data.get("client")

    client = clients.get(client_id)

    if not client:
        return {"reply": "Client not found"}

    if not is_active(client):
        stk_push(client["phone"], 1000)
        return {"reply": "⚠️ Subscription expired"}

    return {"reply": ask_ai(client_id, msg, client)}

# ================= WHATSAPP =================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming = request.form.get("Body", "").lower()
    phone = request.form.get("From", "")

    words = incoming.split()

    client = None
    client_id = None

    for key, c in clients.items():
        if c.get("keyword") in words:
            client = c
            client_id = key
            break

    if not client:
        return Response(
            "<Response><Message>Start with business name</Message></Response>",
            mimetype="text/xml"
        )

    save_lead(phone, incoming, client_id)

    message = " ".join([w for w in words if w != client["keyword"]])

    if not is_active(client):
        stk_push(client["phone"], 1000)
        reply = "⚠️ Subscription expired"
    else:
        reply = ask_ai(phone, message, client)

    return Response(f"<Response><Message>{reply}</Message></Response>", mimetype="text/xml")

# ================= HOME =================
@app.route("/")
def home():
    return "🚀 FlowAI LIVE"

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
