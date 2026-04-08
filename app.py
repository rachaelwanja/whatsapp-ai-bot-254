from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import json
import os
import datetime

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

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
memory = {}   # for AI conversation
state = {}    # for booking flow

# ================= LOAD LEADS =================
try:
    with open("leads.json", "r") as f:
        leads = json.load(f)
except:
    leads = []

def save_leads():
    with open("leads.json", "w") as f:
        json.dump(leads, f, indent=4)

# ================= AI FUNCTION =================
def ask_ai(user, message, client):

    if user not in memory:
        memory[user] = []

    memory[user].append(message)
    memory[user] = memory[user][-5:]

    conversation = "\n".join(memory[user])

    system_prompt = f"""
You are a friendly WhatsApp assistant for {client['name']}.

Business Info:
- Location: {client.get('location')}
- Phone: {client.get('phone')}
- Services: {", ".join(client.get("services", []))}
- Consultation Fee: {client.get("consultation_fee")}

Doctors:
{chr(10).join([f"- {d['name']} ({d['specialty']})" for d in client.get("doctors", [])])}

Rules:
- Be human and friendly
- Keep replies SHORT (max 2 sentences)
- Use simple English
- Guide users to book appointments
"""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": conversation}
                ]
            }
        )

        data = response.json()
        reply = data["choices"][0]["message"]["content"]

        memory[user].append(reply)

        return reply

    except Exception as e:
        print("AI ERROR:", e)
        return "⚠️ Sorry, I'm having a small issue. Try again 😊"

# ================= WHATSAPP ROUTE =================
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
        msg.body("⚠️ Business not configured.")
        return str(resp)

    # ================= BOOKING FLOW =================

    if state.get(user, {}).get("step") == "name":
        state[user] = {"step": "date", "name": incoming_msg}
        msg.body("📅 Enter preferred appointment date")
        return str(resp)

    elif state.get(user, {}).get("step") == "date":
        state[user]["date"] = incoming_msg
        state[user]["step"] = "service"
        msg.body("🩺 What service do you need?")
        return str(resp)

    elif state.get(user, {}).get("step") == "service":

        booking = state[user]

        leads.append({
            "user": user,
            "client": client["name"],
            "name": booking["name"],
            "date": booking["date"],
            "service": incoming_msg,
            "time": str(datetime.datetime.now())
        })

        save_leads()
        state[user] = {}

        msg.body("✅ Appointment booked! We’ll confirm shortly.")
        return str(resp)

    # ================= TRIGGERS =================

    if "book" in lower_msg or "appointment" in lower_msg:
        state[user] = {"step": "name"}
        msg.body("📝 Please enter your full name")
        return str(resp)

    if any(word in lower_msg for word in ["hi", "hello", "hey"]):
        msg.body(client.get("welcome_message", f"Welcome to {client['name']} 😊"))
        return str(resp)

    # ================= AI RESPONSE =================
    reply = ask_ai(user, incoming_msg, client)
    msg.body(reply)

    return str(resp)

# ================= HOME =================
@app.route("/")
def home():
    return "AI Bot (Memory + Booking + OpenRouter) 🚀"

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
