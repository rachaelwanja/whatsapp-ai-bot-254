from flask import Flask, request, jsonify, render_template, redirect, session, Response
import requests, json, os, datetime, base64
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "flowai-secret"

# ================= ENV =================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")

CALLBACK_URL = "https://whatsapp-ai-bot-254-1.onrender.com/mpesa/callback"

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
You are a professional assistant for {client['name']}.
Services: {", ".join(client.get("services", []))}

Be friendly, short and helpful.
Help users book services.
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
        return "⚠️ AI temporarily unavailable."

# ================= PLAN CHECK =================
def is_active(client):
    if client.get("plan") == "paid":
        return True

    expiry = datetime.datetime.fromisoformat(client.get("expiry"))
    return datetime.datetime.now() < expiry

# ================= LEADS =================
def save_lead(phone, message, client_id):

    lead = {
        "phone": phone,
        "message": message,
        "client": client_id,
        "time": str(datetime.datetime.now())
    }

    leads = load_json("leads.json")

    if not isinstance(leads, list):
        leads = []

    leads.append(lead)
    save_json("leads.json", leads)

# ================= MPESA =================
def get_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    res = requests.get(url, auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET))
    return res.json().get("access_token")

def stk_push(phone, amount):

    token = get_token()
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    password = base64.b64encode(
        (MPESA_SHORTCODE + MPESA_PASSKEY + timestamp).encode()
    ).decode()

    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": "FlowAI",
        "TransactionDesc": "Subscription"
    }

    headers = {"Authorization": f"Bearer {token}"}

    requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers=headers
    )

# ================= CALLBACK =================
@app.route("/mpesa/callback", methods=["POST"])
def mpesa_callback():

    data = request.json

    try:
        result = data["Body"]["stkCallback"]
        status = result["ResultCode"]

        items = result.get("CallbackMetadata", {}).get("Item", [])

        phone = None

        for i in items:
            if i["Name"] == "PhoneNumber":
                phone = str(i["Value"])

        if status == 0:
            for k, c in clients.items():
                if c["phone"] in phone:
                    c["plan"] = "paid"
                    c["expiry"] = str(datetime.datetime.now() + timedelta(days=30))

            save_json("clients.json", clients)

    except:
        pass

    return {"ResultCode": 0}

# ================= SIGNUP =================
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        name = request.form.get("name")
        phone = request.form.get("phone")

        clients[username] = {
            "name": name,
            "phone": phone,
            "services": ["Customer Support"],
            "keyword": username,
            "account": {
                "username": username,
                "password": password
            },
            "plan": "trial",
            "expiry": str(datetime.datetime.now() + timedelta(days=3))
        }

        save_json("clients.json", clients)

        return redirect("/login")

    return render_template("signup.html")

# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        for key, c in clients.items():
            if c["account"]["username"] == username and c["account"]["password"] == password:
                session["client"] = key
                return redirect("/dashboard")

    return render_template("login.html")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():

    if "client" not in session:
        return redirect("/login")

    client = clients[session["client"]]

    return render_template("dashboard.html", client=client)

# ================= LEADS API =================
@app.route("/leads")
def view_leads():

    if "client" not in session:
        return redirect("/login")

    client_id = session["client"]

    all_leads = load_json("leads.json")

    if not isinstance(all_leads, list):
        all_leads = []

    client_leads = [l for l in all_leads if l["client"] == client_id]

    return jsonify(client_leads)

# ================= CHAT PAGE =================
@app.route("/chat")
def chat_page():
    client_id = request.args.get("client")
    return render_template("chat.html", client_id=client_id)

# ================= CHAT API =================
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
        return {"reply": "⚠️ Subscription expired. Payment request sent."}

    reply = ask_ai(client_id, msg, client)

    return {"reply": reply}

# ================= WHATSAPP (MULTI-CLIENT + LEADS) =================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming = request.form.get("Body").lower()
    phone = request.form.get("From")

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
            "<Response><Message>⚠️ Start message with business name (e.g. 'bliss hi')</Message></Response>",
            mimetype="text/xml"
        )

    # ✅ SAVE LEAD
    save_lead(phone, incoming, client_id)

    message = " ".join([w for w in words if w != client["keyword"]])

    if not is_active(client):
        stk_push(client["phone"], 1000)
        reply = "⚠️ Subscription expired. Payment request sent."
    else:
        reply = ask_ai(phone, message, client)

    return Response(
        f"<Response><Message>{reply}</Message></Response>",
        mimetype="text/xml"
    )

# ================= HOME =================
@app.route("/")
def home():
    return "🚀 FlowAI SaaS Running"

# ================= RUN =================
if __name__ == "__main__":
    app.run()
