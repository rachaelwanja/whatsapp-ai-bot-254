from flask import Flask, request, jsonify, render_template, redirect, session, Response
import requests, json, os, datetime
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "flowai-secret"

# ================= CONFIG =================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# 🔥 YOUR MPESA SERVICE (Render)
MPESA_API_URL = "https://whatsapp-ai-bot-254-1.onrender.com/stk"

# 🔥 CALLBACK (THIS APP)
BASE_URL = "https://whatsapp-ai-bot-254-1.onrender.com"

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
memory = {}

# ================= PLANS =================
def get_plan_price(plan):
    return {
        "basic": 500,
        "pro": 1000,
        "premium": 2000
    }.get(plan, 500)

# ================= AI =================
def ask_ai(user, message, client):

    memory.setdefault(user, [])
    memory[user] = memory[user][-5:] + [message]

    prompt = f"You are assistant for {client['name']}. Be helpful and short."

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

    return datetime.datetime.now() < datetime.datetime.fromisoformat(expiry)

def get_days_left(client):
    expiry = client.get("expiry")
    if not expiry:
        return 0

    delta = datetime.datetime.fromisoformat(expiry) - datetime.datetime.now()
    return max(delta.days, 0)

# ================= LEADS =================
def save_lead(phone, message):

    leads = load_json("leads.json")

    if not isinstance(leads, list):
        leads = []

    leads.append({
        "phone": phone,
        "message": message,
        "time": str(datetime.datetime.now())
    })

    save_json("leads.json", leads)

# ================= MPESA =================
def stk_push(phone, amount):
    try:
        requests.post(MPESA_API_URL, json={
            "phone": phone,
            "amount": amount
        })
    except:
        pass

# ================= SAVE PAYMENT =================
@app.route("/save_payment", methods=["POST"])
def save_payment():

    data = request.json

    payments = load_json("payments.json")

    if not isinstance(payments, list):
        payments = []

    payments.append({
        "phone": data["phone"],
        "amount": data["amount"],
        "status": data["status"],
        "time": str(datetime.datetime.now())
    })

    save_json("payments.json", payments)

    return {"status": "saved"}

# ================= ACTIVATE PLAN =================
@app.route("/activate", methods=["POST"])
def activate():

    data = request.json
    phone = str(data.get("phone"))
    amount = int(data.get("amount", 0))

    for client in clients.values():

        if phone in client.get("phones", []):

            # 🔥 AUTO PLAN BASED ON PAYMENT
            if amount >= 2000:
                client["tier"] = "premium"
            elif amount >= 1000:
                client["tier"] = "pro"
            else:
                client["tier"] = "basic"

            client["plan"] = "paid"
            client["expiry"] = str(datetime.datetime.now() + timedelta(days=30))

    save_json("clients.json", clients)

    return {"status": "activated"}

# ================= AUTH =================
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        name = request.form.get("name")

        if username in clients:
            return "User exists"

        clients[username] = {
            "name": name,
            "phones": ["14155238886"],
            "account": {"username": username, "password": password},
            "tier": "basic",
            "plan": "trial",
            "expiry": str(datetime.datetime.now() + timedelta(days=3))
        }

        save_json("clients.json", clients)

        session["client"] = username
        return redirect("/dashboard")

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

    client = clients[session["client"]]

    status = "ACTIVE ✅" if is_active(client) else "EXPIRED ❌"
    days_left = get_days_left(client)

    return render_template(
        "dashboard.html",
        client=client,
        status=status,
        days_left=days_left
    )

# ================= PRICING =================
@app.route("/pricing")
def pricing():
    return render_template("pricing.html")

@app.route("/set_plan", methods=["POST"])
def set_plan():

    data = request.json
    plan = data.get("plan")

    client = clients[session["client"]]
    client["tier"] = plan

    save_json("clients.json", clients)

    return {"status": "ok"}

@app.route("/pay", methods=["POST"])
def pay():

    client = clients[session["client"]]
    amount = get_plan_price(client.get("tier"))

    # 🔥 YOUR SAFARICOM NUMBER
    stk_push("254115126566", amount)

    return {"message": f"📲 STK sent (KES {amount})"}

# ================= WHATSAPP =================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming = request.form.get("Body", "")
    from_number = request.form.get("From")
    to_number = request.form.get("To").replace("whatsapp:+", "")

    client = None
    for c in clients.values():
        if to_number in c.get("phones", []):
            client = c
            break

    if not client:
        return Response("<Response><Message>No business found</Message></Response>", mimetype="text/xml")

    # 🔥 SAVE LEAD
    save_lead(from_number, incoming)

    # 🔥 BUY COMMAND
    if incoming.lower() == "buy":
        amount = get_plan_price(client.get("tier"))
        stk_push("254115126566", amount)
        return Response("<Response><Message>📲 Processing payment... check phone</Message></Response>", mimetype="text/xml")

    # 🔥 CHECK PLAN
    if not is_active(client):
        return Response("<Response><Message>⚠️ Expired. Reply BUY to renew</Message></Response>", mimetype="text/xml")

    reply = ask_ai(from_number, incoming, client)

    return Response(f"<Response><Message>{reply}</Message></Response>", mimetype="text/xml")

# ================= HOME =================
@app.route("/")
def home():
    return "🚀 FlowAI LIVE"

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
