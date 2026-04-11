from flask import Flask, request, jsonify, render_template
import json
import os
from datetime import datetime

app = Flask(__name__)

# ---------------------------
# FILES
# ---------------------------
CLIENTS_FILE = "clients.json"
LEADS_FILE = "leads.json"

# ---------------------------
# HELPERS
# ---------------------------
def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ---------------------------
# LOAD DATA
# ---------------------------
clients = load_json(CLIENTS_FILE)
leads = load_json(LEADS_FILE)

# ---------------------------
# CHAT ENDPOINT (for widget)
# ---------------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "").lower()

    if "price" in message:
        return jsonify({"reply": "Our pricing starts at KES 500 😊"})
    
    return jsonify({"reply": "Hello! How can I help you today?"})


# ---------------------------
# WHATSAPP WEBHOOK
# ---------------------------
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    global leads, clients

    incoming_msg = request.values.get("Body", "").lower()
    phone = request.values.get("From", "")

    DEFAULT_BUSINESS = "bliss"

    parts = incoming_msg.split()

    # ---------------------------
    # FIXED MESSAGE PARSING
    # ---------------------------
    if len(parts) < 2:
        business = DEFAULT_BUSINESS
        user_msg = incoming_msg
    else:
        business = parts[0]
        user_msg = " ".join(parts[1:])

    # ---------------------------
    # CREATE CLIENT IF NOT EXISTS
    # ---------------------------
    if business not in clients:
        clients[business] = {
            "name": business,
            "revenue": 0,
            "customers": []
        }

    # ---------------------------
    # SAVE LEAD
    # ---------------------------
    leads[phone] = {
        "phone": phone,
        "business": business,
        "last_message": user_msg,
        "time": str(datetime.now())
    }

    save_json(LEADS_FILE, leads)

    # ---------------------------
    # SIMPLE BOT LOGIC
    # ---------------------------
    reply = ""

    if "hi" in user_msg or "hello" in user_msg:
        reply = f"Hello 👋 Welcome to {business.capitalize()}! How can I help you?"

    elif "price" in user_msg or "pricing" in user_msg:
        reply = "Our pricing starts from KES 500 💰"

    elif "buy" in user_msg or "pay" in user_msg:
        reply = "To proceed with payment, we will send you an M-Pesa prompt shortly 📲"

        # simulate revenue
        clients[business]["revenue"] += 500
        clients[business]["customers"].append(phone)
        save_json(CLIENTS_FILE, clients)

    else:
        reply = "Sorry, I didn’t understand. Try asking about pricing 😊"

    return reply


# ---------------------------
# DASHBOARD
# ---------------------------
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", clients=clients)


# ---------------------------
# ADMIN DASHBOARD
# ---------------------------
@app.route("/admin")
def admin():
    total_revenue = sum(c["revenue"] for c in clients.values())

    return render_template(
        "admin.html",
        clients=clients,
        leads=leads,
        total_revenue=total_revenue
    )


# ---------------------------
# HOME
# ---------------------------
@app.route("/")
def home():
    return "Bot is running 🚀"


# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)
