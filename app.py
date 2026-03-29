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

# ================= AI (OPENROUTER) =================
def ai_reply(user, text, client):
    try:
        if user not in memory:
            memory[user] = {"history": []}

        memory[user]["history"].append(text)
        memory[user]["history"] = memory[user]["history"][-5:]

        conversation = "\n".join(memory[user]["history"])

        prompt = f"""
You are a friendly WhatsApp receptionist for {client['name']}.

Rules:
- Be natural and human
- Keep replies short
- Use emojis sometimes 😊
- Guide the user helpfully

Business Type: {client['type']}
Location: {client.get('location', 'Kenya')}

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
            <b>Details:</b> {lead.get('details', '')} <br>
            <b>Time:</b> {lead['time']}
            </p>
            <hr>
            """

    return html

# ================= WHATSAPP =================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    global clients
    clients = load_clients()

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

    # ================= BOOKING FLOW =================
    if memory.get(user, {}).get("state") == "booking_name":
        memory[user] = {"state": "booking_date", "name": incoming_msg}
        msg.body("📅 Enter preferred appointment date")
        return str(resp)

    elif memory.get(user, {}).get("state") == "booking_date":
        memory[user]["date"] = incoming_msg
        memory[user]["state"] = "booking_service"
        msg.body("🩺 What service do you need?")
        return str(resp)

    elif memory.get(user, {}).get("state") == "booking_service":
        booking = memory[user]

        leads.append({
            "user": user,
            "client": client["name"],
            "name": booking["name"],
            "date": booking["date"],
            "service": incoming_msg,
            "time": str(datetime.datetime.now())
        })

        save_leads()
        memory[user] = {}

        msg.body("✅ Appointment request received! We'll confirm shortly.")
        return str(resp)

    # ================= MAIN MENU =================
    if lower_msg in ["hi", "hello", "hey", "menu"]:
        reply = f"👋 Welcome to {client['name']}!\n"

        if client["type"] == "hospital":
            reply += """
1️⃣ Services
2️⃣ Doctors
3️⃣ Book Appointment
4️⃣ Location
5️⃣ Emergency
"""
        else:
            reply += "How can we help you today?"

        msg.body(reply)
        return str(resp)

    # ================= HOSPITAL =================
    if client["type"] == "hospital":

        if lower_msg in ["1", "services"]:
            services = "\n".join([f"✔️ {s}" for s in client.get("services", [])])
            reply = f"🩺 Services:\n{services}"

        elif lower_msg in ["2", "doctors"]:
            doctors = ""
            for d in client.get("doctors", []):
                doctors += f"\n👨‍⚕️ {d['name']} ({d['specialty']})\n🕒 {d['availability']}\n"
            reply = f"👩‍⚕️ Doctors:\n{doctors}"

        elif lower_msg in ["3", "book", "appointment"]:
            memory[user] = {"state": "booking_name"}
            reply = "📝 Please enter your full name"

        elif lower_msg in ["4", "location"]:
            reply = f"📍 {client.get('location')}"

        elif lower_msg in ["5", "emergency"]:
            reply = client.get("emergency")

        elif "fee" in lower_msg:
            reply = f"💰 Consultation fee: {client.get('consultation_fee')}"

        elif "insurance" in lower_msg:
            reply = client.get("faq", {}).get("insurance", "")

        elif "lab" in lower_msg:
            reply = client.get("faq", {}).get("lab_time", "")

        elif "payment" in lower_msg:
            reply = client.get("faq", {}).get("payment", "")

        else:
            reply = ai_reply(user, incoming_msg, client)

    else:
        reply = ai_reply(user, incoming_msg, client)

    msg.body(reply)
    return str(resp)

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
