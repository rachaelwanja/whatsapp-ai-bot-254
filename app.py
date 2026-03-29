from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os
import json
import datetime
import requests

app = Flask(__name__)

# ================= LOAD CLIENTS =================
def load_clients():
    try:
        with open("clients.json", "r") as f:
            return json.load(f)
    except:
        return {}

clients = load_clients()

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

# ================= OPENROUTER AI =================
def ai_reply(user, text, client):

    try:
        if user not in memory:
            memory[user] = {"history": []}

        memory[user]["history"].append(text)
        memory[user]["history"] = memory[user]["history"][-5:]

        conversation = "\n".join(memory[user]["history"])

        prompt = f"""
You are a smart WhatsApp assistant for a {client['type']} business.

Business Name: {client['name']}
Location: {client.get('location', 'Kenya')}

Your job:
- Be friendly and human
- Keep replies SHORT (WhatsApp style)
- Answer based on the business
- If it's not related, answer generally but naturally

Conversation:
{conversation}
"""

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ]
            }
        )

        data = response.json()

        reply = data["choices"][0]["message"]["content"]

        memory[user]["history"].append(reply)

        return reply

    except Exception as e:
        print("AI ERROR:", e)
        return "⚠️ AI temporarily unavailable."

# ================= HOME =================
@app.route("/")
def home():
    return "WhatsApp AI Bot Running 🚀"

# ================= DASHBOARD =================
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

    global clients
    clients = load_clients()  # 🔥 reload every request

    incoming_msg = request.values.get("Body", "").strip()
    lower_msg = incoming_msg.lower()
    user = request.values.get("From")
    to_number = request.values.get("To")

    resp = MessagingResponse()
    msg = resp.message()

    client = clients.get(to_number)

    if not client:
        msg.body("⚠️ This business is not configured yet.")
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

        msg.body("✅ Thanks! We’ll contact you shortly.")
        return str(resp)

    # ================= SMART MENU =================
    if lower_msg in ["hi", "hello", "hey", "menu"]:

        if client["type"] == "school":
            reply = f"""
🏫 {client['name']}

1️⃣ Admissions
2️⃣ Fees
3️⃣ Location
"""

        elif client["type"] == "hospital":
            reply = f"""
🏥 {client['name']}

1️⃣ Services
2️⃣ Location
3️⃣ Book Appointment
"""

        elif client["type"] == "matatu":
            reply = f"""
🚐 {client['name']}

1️⃣ Routes
2️⃣ Fare
"""

        else:
            reply = f"Welcome to {client['name']} 😊"

    # ================= SCHOOL =================
    elif client["type"] == "school":

        if lower_msg == "1":
            reply = "Admissions open 👍 Send student details."
        elif lower_msg == "2":
            reply = f"Fees: {client.get('fees', 'Contact school')}"
        elif lower_msg == "3":
            reply = f"Location: {client.get('location')}"
        else:
            reply = ai_reply(user, incoming_msg, client)

    # ================= HOSPITAL =================
    elif client["type"] == "hospital":

        if lower_msg == "1":
            reply = f"Services: {client.get('services')}"
        elif lower_msg == "2":
            reply = f"Location: {client.get('location')}"
        elif lower_msg == "3":
            memory[user] = {"state": "booking"}
            reply = "Send your name + preferred date 📅"
        else:
            reply = ai_reply(user, incoming_msg, client)

    # ================= MATATU =================
    elif client["type"] == "matatu":

        if lower_msg == "1":
            reply = f"Routes: {client.get('routes')}"
        elif lower_msg == "2":
            reply = f"Fare: {client.get('fare')}"
        else:
            reply = ai_reply(user, incoming_msg, client)

    else:
        reply = ai_reply(user, incoming_msg, client)

    msg.body(reply)
    return str(resp)

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
