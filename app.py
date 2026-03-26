from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai
import os
import time

app = Flask(__name__)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# ================= CLIENT DATABASE =================
clients = {
    "whatsapp:+14155238886": {  # Example number
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

memory = {}

# ================= ROUTES =================

@app.route("/")
def home():
    return "Multi-client bot running 🚀"


@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "").strip().lower()
    user = request.values.get("From")
    to_number = request.values.get("To")  # 🔥 KEY

    resp = MessagingResponse()
    msg = resp.message()

    # Get client data
    client = clients.get(to_number)

    if not client:
        msg.body("⚠️ Client not configured.")
        return str(resp)

    # ================= SCHOOL =================
    if client["type"] == "school":

        if incoming_msg in ["hi", "hello", "menu"]:
            reply = f"""
🏫 {client['name']}

1️⃣ Admissions
2️⃣ Fees
3️⃣ Location
"""

        elif incoming_msg == "1":
            reply = "Admissions open. Send student details."

        elif incoming_msg == "2":
            reply = f"Fees: {client['fees']}"

        elif incoming_msg == "3":
            reply = f"Location: {client['location']}"

        else:
            reply = ai_reply(user, incoming_msg)

    # ================= HOSPITAL =================
    elif client["type"] == "hospital":

        if incoming_msg in ["hi", "hello", "menu"]:
            reply = f"""
🏥 {client['name']}

1️⃣ Services
2️⃣ Location
3️⃣ Book Appointment
"""

        elif incoming_msg == "1":
            reply = f"Services: {client['services']}"

        elif incoming_msg == "2":
            reply = f"Location: {client['location']}"

        elif incoming_msg == "3":
            reply = "Send your name and preferred date."

        else:
            reply = ai_reply(user, incoming_msg)

    # ================= MATATU =================
    elif client["type"] == "matatu":

        if incoming_msg in ["hi", "hello", "menu"]:
            reply = f"""
🚐 {client['name']}

1️⃣ Routes
2️⃣ Fare
"""

        elif incoming_msg == "1":
            reply = f"Routes: {client['routes']}"

        elif incoming_msg == "2":
            reply = f"Fare: {client['fare']}"

        else:
            reply = ai_reply(user, incoming_msg)

    else:
        reply = "Service not available."

    time.sleep(1)
    msg.body(reply)
    return str(resp)


# ================= AI FUNCTION =================

def ai_reply(user, text):

    try:
        if user not in memory:
            memory[user] = []

        memory[user].append(text)
        memory[user] = memory[user][-5:]

        conversation = "\n".join(memory[user])

        model = genai.GenerativeModel("gemini-1.5-flash")

        response = model.generate_content(
            f"Reply briefly:\n{conversation}"
        )

        reply = response.text if response.text else "Ask me something 😊"

        memory[user].append(reply)

        return reply

    except:
        return "⚠️ AI unavailable."
