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
clients = [
    {
        "type": "school",
        "name": "Thika Primary School",
        "fees": "KSh 40,000 per term",
        "location": "Thika Town"
    },
    {
        "type": "hospital",
        "name": "City Clinic",
        "services": "General consultation, maternity",
        "location": "Nairobi"
    },
    {
        "type": "matatu",
        "name": "Super Metro",
        "routes": "Nairobi ↔ Thika",
        "fare": "KSh 100"
    }
]

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
    return "WhatsApp AI Bot Running 🚀"

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
            <b>Business:</b> {lead['client']} <br>
            <b>User:</b> {lead['user']} <br>
            <b>Details:</b> {lead['details']} <br>
            <b>Time:</b> {lead['time']}
            </p><hr>
            """

    return html

# ================= DETECT CLIENT =================
def detect_client(message):
    msg = message.lower()

    if "school" in msg or "admission" in msg:
        return next(c for c in clients if c["type"] == "school")

    elif "hospital" in msg or "doctor" in msg:
        return next(c for c in clients if c["type"] == "hospital")

    elif "matatu" in msg or "fare" in msg or "route" in msg:
        return next(c for c in clients if c["type"] == "matatu")

    return clients[0]  # default

# ================= WHATSAPP =================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "").strip()
    lower_msg = incoming_msg.lower()
    user = request.values.get("From")

    resp = MessagingResponse()
    msg = resp.message()

    client = detect_client(incoming_msg)

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

        msg.body("✅ Got it! We'll contact you shortly 👍")
        return str(resp)

    # ================= SIMPLE MENUS =================
    if lower_msg in ["hi", "hello", "menu"]:
        reply = f"""
👋 Hi! Welcome to our service

Choose:
1️⃣ School
2️⃣ Hospital
3️⃣ Matatu
"""
        msg.body(reply)
        return str(resp)

    if lower_msg == "1":
        client = next(c for c in clients if c["type"] == "school")
        msg.body(f"🏫 {client['name']}\nFees: {client['fees']}\nReply 'admission' to enroll")
        return str(resp)

    if lower_msg == "2":
        client = next(c for c in clients if c["type"] == "hospital")
        memory[user] = {"state": "booking"}
        msg.body(f"🏥 {client['name']}\nSend your name + appointment date")
        return str(resp)

    if lower_msg == "3":
        client = next(c for c in clients if c["type"] == "matatu")
        msg.body(f"🚐 {client['name']}\nFare: {client['fare']}\nRoutes: {client['routes']}")
        return str(resp)

    # ================= AI RESPONSE =================
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

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": f"""
You are a friendly WhatsApp assistant for {client['name']} in {client.get('location', 'Kenya')}.

RULES:
- Sound human (like chatting on WhatsApp)
- Keep replies SHORT (1–3 sentences)
- Be friendly and simple
- Don't be too formal
- Only talk about the business when needed
- If question is general, answer normally

Tone:
- Friendly 😊
- Kenyan vibe (simple English)

"""
                    },
                    {
                        "role": "user",
                        "content": conversation
                    }
                ],
                "max_tokens": 150
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
