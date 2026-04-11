from flask import Flask, request, jsonify, render_template
import json
import os

app = Flask(__name__)

# =========================
# FILE HELPERS
# =========================
def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# =========================
# LOAD DATA
# =========================
CLIENTS_FILE = "clients.json"
LEADS_FILE = "leads.json"

clients = load_json(CLIENTS_FILE)
leads = load_json(LEADS_FILE)

# =========================
# CHATBOT LOGIC
# =========================
def get_reply(message):
    message = message.lower()

    if "hi" in message or "hello" in message:
        return "Hello 👋 Welcome! How can I help you?"

    if "price" in message or "cost" in message:
        return "Our bot costs KSh 1000/month 💰"

    if "buy" in message or "start" in message:
        return "Great! Send your name to get started 🚀"

    return "Sorry, I didn’t understand. Try asking about pricing 😊"

# =========================
# WHATSAPP WEBHOOK
# =========================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    data = request.form

    phone = data.get("From")
    message = data.get("Body")

    # Save lead
    leads[phone] = {
        "message": message
    }
    save_json(LEADS_FILE, leads)

    reply = get_reply(message)

    return f"""
    <Response>
        <Message>{reply}</Message>
    </Response>
    """

# =========================
# WEB CHAT API
# =========================
@app.route("/chat_api", methods=["POST"])
def chat_api():
    data = request.json
    message = data.get("message")
    client_id = data.get("client", "demo")

    reply = get_reply(message)

    return jsonify({"reply": reply})

# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    total_leads = len(leads)

    total_revenue = 0
    for c in clients.values():
        if c.get("plan") == "pro":
            total_revenue += 1000

    return render_template(
        "dashboard.html",
        total_leads=total_leads,
        total_revenue=total_revenue
    )

# =========================
# ADMIN PANEL
# =========================
@app.route("/admin")
def admin():
    total_clients = len(clients)
    total_leads = len(leads)

    total_revenue = 0
    for c in clients.values():
        if c.get("plan") == "pro":
            total_revenue += 1000

    return render_template(
        "admin.html",
        clients=clients,
        total_clients=total_clients,
        total_leads=total_leads,
        total_revenue=total_revenue
    )

# =========================
# CHAT PAGE
# =========================
@app.route("/chat")
def chat():
    return render_template("chat.html")

# =========================
# HOME
# =========================
@app.route("/")
def home():
    return "Bot is running 🚀"

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
