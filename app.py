from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai
import os
import time
import random
from datetime import datetime

app = Flask(__name__)

# Configure Gemini AI
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Memory storage
memory = {}
leads = {}

@app.route("/")
def home():
    return "WhatsApp AI bot running"

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "")
    incoming_msg = incoming_msg.strip() if incoming_msg else ""
    user = request.values.get("From")

    resp = MessagingResponse()
    msg = resp.message()

    text = incoming_msg.lower()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ---------- LOG USER MESSAGE ----------
    with open("chat_log.txt", "a") as log:
        log.write(f"{timestamp} | {user} | USER: {incoming_msg}\n")

    # ---------- RESET ----------
    if text == "reset":
        memory[user] = []
        leads[user] = {}
        reply = "🔄 Conversation reset. How can I help you today?"

    # ---------- GREETING ----------
    elif text in ["hi", "hello", "hey"]:
        greetings = [
            "Hello 👋 I'm your AI assistant. How can I help you today?",
            "Hi there! 😊 What can I assist you with?",
            "Hey! I'm here to help. Ask me anything."
        ]
        reply = random.choice(greetings)

    # ---------- MENU ----------
    elif text in ["menu", "help"]:
        reply = (
            "🤖 AI Assistant Menu\n\n"
            "1️⃣ Ask any question\n"
            "2️⃣ School Information\n"
            "3️⃣ Book Service\n"
            "4️⃣ Reset\n\n"
            "Type your option or message."
        )

    # ---------- SCHOOL ----------
    elif "school" in text or "thika primary" in text:
        reply = (
            "🏫 *Thika Primary School (Demo)*\n\n"
            "Choose an option:\n\n"
            "1️⃣ Admissions\n"
            "2️⃣ Fees\n"
            "3️⃣ Location\n"
            "4️⃣ Contact\n\n"
            "Reply with 1, 2, 3 or 4"
        )

    elif text == "1" or "admission" in text:
        reply = (
            "📚 *Admissions for 2026 are open.*\n\n"
            "Please provide:\n"
            "• Student Name\n"
            "• Grade\n"
            "• Parent phone number"
        )

    elif text == "2" or "fees" in text:
        reply = (
            "💰 *School Fees*\n\n"
            "Lower Primary: KSh 400 per term\n"
            "Upper Primary: KSh 550 per term\n\n"
            "Contact office for details."
        )

    elif text == "3" or "location" in text:
        reply = (
            "📍 *Location*\n"
            "Thika Town\n"
            "Office Hours: 8:00 AM – 4:00 PM"
        )

    elif text == "4" or "contact" in text:
        reply = (
            "📞 *Contact Office*\n"
            "Phone: +254700000000\n"
            "Email: info@thikaprimary.ac.ke"
        )

    # ---------- LEAD CAPTURE ----------
    elif "book" in text or "service" in text:
        leads[user] = {"service": incoming_msg}
        reply = "Great! What is your name?"

    elif user in leads and "name" not in leads[user]:
        leads[user]["name"] = incoming_msg
        reply = "Thank you! We will contact you shortly."

    # ---------- AI CHAT ----------
    else:
        try:
            if user not in memory:
                memory[user] = []

            memory[user].append(incoming_msg)
            memory[user] = memory[user][-6:]

            conversation = "\n".join(memory[user])

            model = genai.GenerativeModel("gemini-1.5-flash")

            response = model.generate_content(
                f"""
You are a helpful WhatsApp AI assistant.
Keep responses short and clear.

Conversation:
{conversation}
"""
            )

            reply = response.text if response.text else "I'm here 😊 Ask me anything."

            memory[user].append(reply)

        except Exception as e:
            print("AI ERROR:", e)
            reply = "⚠️ AI temporarily unavailable. Try again."

    # ---------- LOG BOT RESPONSE ----------
    with open("chat_log.txt", "a") as log:
        log.write(f"{timestamp} | BOT: {reply}\n")

    time.sleep(1)

    msg.body(reply)
    return str(resp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
