from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os
import json
import datetime
import requests

app = Flask(__name__)

# ================= CONFIG =================
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# ================= LOAD CLIENTS =================
def load_clients():
    try:
        with open("clients.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print("CLIENT LOAD ERROR:", e)
        return {}

clients = load_clients()

# ================= MEMORY =================
memory = {}

# ================= LEADS =================
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
    return "🚀 WhatsApp Multi-Business AI Bot Running"

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

    incoming_msg = request.values.get("Body", "").strip()
    lower_msg = incoming_msg.lower()
    user = request.values.get("From")
    to_number = request.values.get("To")

    print("TO NUMBER:", to_number)

    resp = MessagingResponse()
    msg = resp.message()

    client = clients.get(to_number)

    if not client:
        msg.body("⚠️ This business is not configured yet.")
        return str(resp)

    # ================= BOOKING MODE =================
    if memory.get(user, {}).get("state") == "booking":

        leads.append({
            "user": user,
            "details": incoming_msg,
            "client": client["name"],
            "time": str(datetime.datetime.now())
        })

        save_leads()
        memory[user] = {}

        msg.body("✅ Thank you! Your request has been received. We’ll contact you shortly.")
        return str(resp)

    # ================= GREETING =================
    if lower_msg in ["hi", "hello", "hey"]:

        reply = f"""
👋 Welcome to {client['name']}

How can we assist you today?

1️⃣ Services
2️⃣ Doctors
3️⃣ Consultation Fee
4️⃣ Location
5️⃣ Book Appointment
"""

        msg.body(reply)
        return str(resp)

    # ================= MENU =================
    if lower_msg == "1":
        reply = "🩺 Our Services:\n" + "\n".join([f"- {s}" for s in client.get("services", [])])

    elif lower_msg == "2":
        doctors = client.get("doctors", [])
        if doctors:
            reply = "👨‍⚕️ Available Doctors:\n"
            for d in doctors:
                reply += f"\n- {d['name']} ({d['specialty']})\n  🕒 {d['availability']}"
        else:
            reply = "No doctors listed."

    elif lower_msg == "3":
        reply = f"💰 Consultation Fee: {client.get('consultation_fee', 'Not specified')}"

    elif lower_msg == "4":
        reply = f"📍 Location: {client.get('location', 'Not available')}"

    elif lower_msg == "5":
        memory[user] = {"state": "booking"}
        reply = "📅 Please send your name and preferred appointment date."

    else:
        reply = ai_reply(user, incoming_msg, client)

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

        prompt = f"""
You are a friendly and professional assistant for {client['name']}.

Talk naturally like a human (WhatsApp style).
Keep answers short, clear, and helpful.

Business info:
- Location: {client.get('location')}
- Services: {", ".join(client.get("services", []))}
- Consultation Fee: {client.get("consultation_fee")}

Conversation:
{conversation}
"""

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o-mini",
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

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
