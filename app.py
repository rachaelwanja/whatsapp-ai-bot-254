from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import os
import json
import datetime

app = Flask(__name__)

# ================= OPENROUTER CONFIG =================
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# ================= CLIENT DATABASE =================
clients = {
    "whatsapp:+14155238886": {
        "type": "school",
        "name": "Thika Primary School",
        "fees": "KSh 40,000 per term",
        "location": "Thika Town"
    },
    "whatsapp:+14155238887": {
        "type": "hospital",
        "name": "City Clinic",
        "services": "General consultation, maternity",
        "location": "Nairobi"
    },
    "whatsapp:+14155238888": {
        "type": "matatu",
        "name": "Super Metro",
        "routes": "Nairobi ↔ Thika",
        "fare": "KSh 100"
    }
}

# ================= MEMORY =================
memory = {}

# ================= LOAD LEADS =================
try:
    with open("leads.json", "r") as f:
        leads = json.load(f)
except:
    leads = []

def save_leads():
    with open("leads.json", "w") as f:
        json.dump(leads, f, indent=4)

# ================= HOME =================
@app.route("/")
def home():
    return "WhatsApp AI Bot (OpenRouter) Running 🚀"

# ================= LEADS DASHBOARD =================
@app.route("/leads")
def view_leads():

    html = "<h2>📋 Captured Leads</h2><hr>"

    if not leads:
        html += "<p>No leads yet.</p>"
    else:
        for lead in leads:
            html += f"""
            <p>
            <b>Client:</b> {lead['client']} <br>
            <b>User:</b> {lead['user']} <br>
            <b>Details:</b> {lead['details']} <br>
            <b>Time:</b> {lead['time']}
            </p>
            <hr>
            """

    return html

# ================= WHATSAPP =================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "").strip()
    lower_msg = incoming_msg.lower()
    user = request.values.get("From")
    to_number = request.values.get("To")

    resp = MessagingResponse()
    msg = resp.message()

    client = clients.get(to_number)

    if not client:
        msg.body("⚠️ Client not configured.")
        return str(resp)

    # ================= LEAD CAPTURE =================
    if memory.get(user, {}).get("state") == "booking":

        leads.append({
            "user": user,
            "details": incoming_msg,
            "client": client["name"],
            "time": str(datetime.datetime.now())
        })

        save_leads()
        memory[user] = {}

        msg.body("✅ Request received. We will contact you shortly.")
        return str(resp)

    # ================= SCHOOL =================
    if client["type"] == "school":

        if lower_msg in ["hi", "hello", "menu"]:
            reply = f"""
🏫 {client['name']}

1️⃣ Admissions  
2️⃣ Fees  
3️⃣ Location
"""

        elif lower_msg == "1":
            memory[user] = {"state": "booking"}
            reply = "Send student details to apply."

        elif lower_msg == "2":
            reply = f"Fees: {client['fees']}"

        elif lower_msg == "3":
            reply = f"Location: {client['location']}"

        else:
            reply = ai_reply(user, incoming_msg, client)

    # ================= HOSPITAL =================
    elif client["type"] == "hospital":

        if lower_msg in ["hi", "hello", "menu"]:
            reply = f"""
🏥 {client['name']}

1️⃣ Services  
2️⃣ Location  
3️⃣ Book Appointment
"""

        elif lower_msg == "1":
            reply = f"Services: {client['services']}"

        elif lower_msg == "2":
            reply = f"Location: {client['location']}"

        elif lower_msg == "3":
            memory[user] = {"state": "booking"}
            reply = "Send your name and preferred date."

        else:
            reply = ai_reply(user, incoming_msg, client)

    # ================= MATATU =================
    elif client["type"] == "matatu":

        if lower_msg in ["hi", "hello", "menu"]:
            reply = f"""
🚐 {client['name']}

1️⃣ Routes  
2️⃣ Fare
"""

        elif lower_msg == "1":
            reply = f"Routes: {client['routes']}"

        elif lower_msg == "2":
            reply = f"Fare: {client['fare']}"

        else:
            reply = ai_reply(user, incoming_msg, client)

    else:
        reply = "Service not available."

    msg.body(reply)
    return str(resp)

# ================= AI FUNCTION =================
def ai_reply(user, text, client):

    try:
        if user not in memory:
            memory[user] = {"history": []}

        memory[user]["history"].append(text)
        memory[user]["history"] = memory[user]["history"][-5:]

        conversation = "\n".join(memory[user]["history"])

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mixtral-8x7b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": f"""
You are a WhatsApp assistant for {client['name']} ({client['type']} in Kenya).

Rules:
- Keep replies VERY SHORT (1–2 sentences)
- Be direct and helpful
- Always guide user to next step (book, ask details, visit, etc.)
"""
                    },
                    {
                        "role": "user",
                        "content": conversation
                    }
                ]
            }
        )

        result = response.json()

        reply = result["choices"][0]["message"]["content"]

        memory[user]["history"].append(reply)

        return reply

    except Exception as e:
        print("AI ERROR:", e)
        return "⚠️ AI temporarily unavailable."

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
