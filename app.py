from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai
import os
import time
import random
from datetime import datetime

app = Flask(__name__)

# ✅ Configure Gemini API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Memory storage
memory = {}

# Lead capture
leads = {}

@app.route("/")
def home():
    return "WhatsApp AI bot running 🚀"


@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "").strip()
    user = request.values.get("From")

    resp = MessagingResponse()
    msg = resp.message()

    text = incoming_msg.lower()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ✅ LOG USER MESSAGE
    with open("chat_log.txt", "a") as log:
        log.write(f"{timestamp} | {user} | USER: {incoming_msg}\n")

    # ---------- RESET ----------
    if text == "reset":
        memory[user] = []
        leads[user] = {}
        reply = "🔄 Conversation reset. How can I help you today?"

    # ---------- GREETING ----------
    elif text in ["hi", "hello", "hey"]:
        reply = random.choice([
            "Hello 👋 I'm your AI assistant. How can I help you today?",
            "Hi there! 😊 What can I assist you with?",
            "Hey! I'm here to help. Ask me anything.",
            "Hello! 👋 How may I assist you today?"
        ])

    # ---------- MENU ----------
    elif text in ["menu", "help"]:
        reply = (
            "🤖 AI Assistant Menu\n\n"
            "1️⃣ Ask any question\n"
            "2️⃣ Get information\n"
            "3️⃣ Chat with AI\n"
            "4️⃣ School Demo\n\n"
            "Just send your message."
        )

    # ---------- SCHOOL DEMO ----------
    elif "school" in text:
        reply = (
            "🏫 *Thika Primary School (Demo)*\n\n"
            "1️⃣ Admissions\n"
            "2️⃣ Fees\n"
            "3️⃣ Location\n"
            "4️⃣ Contact"
        )

    elif "admission" in text:
        reply = "📚 Admissions open. Send student name, grade, and parent contact."

    elif "fees" in text:
        reply = "💰 Lower Primary: KSh 40,000 | Upper Primary: KSh 55,000 per term."

    elif "location" in text:
        reply = "📍 Thika Town. Open 8AM - 4PM."

    # ---------- LEAD CAPTURE ----------
    elif "book" in text or "service" in text:
        leads[user] = {"service": incoming_msg}
        reply = "Great! What is your name?"

    elif user in leads and "name" not in leads[user]:
        leads[user]["name"] = incoming_msg
        reply = "Thanks! Our team will contact you."

    # ---------- AI CHAT ----------
    else:
        try:
            if user not in memory:
                memory[user] = []

            memory[user].append(incoming_msg)

            # Keep last 6 messages only
            memory[user] = memory[user][-6:]

            conversation = "\n".join(memory[user])

            # ✅ Gemini model
            model = genai.GenerativeModel("gemini-1.5-flash")

            response = model.generate_content(
                f"You are a helpful WhatsApp AI assistant. Reply briefly.\n\n{conversation}"
            )

            reply = response.text if response.text else "Ask me anything 😊"

            memory[user].append(reply)

        except Exception as e:
            print("AI ERROR:", e)
            reply = "⚠️ AI temporarily unavailable. Try again."

    # ✅ LOG BOT RESPONSE
    with open("chat_log.txt", "a") as log:
        log.write(f"{timestamp} | BOT: {reply}\n")

    # Simulate human delay
    time.sleep(1)

    msg.body(reply)
    return str(resp)


# ✅ RUN SERVER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
