from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
import os
import time
import random
from datetime import datetime

app = Flask(__name__)

# Initialize Gemini
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Memory storage
memory = {}

# Lead capture
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

    # LOG USER MESSAGE
    with open("chat_log.txt", "a") as log:
        log.write(f"{timestamp} | {user} | USER: {incoming_msg}\n")

    if text == "reset":
        memory[user] = []
        leads[user] = {}
        reply = "🔄 Conversation reset. How can I help you today?"
        msg.body(reply)
        return str(resp)

    elif text in ["hi", "hello", "hey"]:
        reply = random.choice([
            "Hello 👋 I'm your AI assistant. How can I help you today?",
            "Hi there! 😊 What can I assist you with?",
            "Hey! I'm here to help. Ask me anything.",
            "Hello! 👋 How may I assist you today?"
        ])

    elif text in ["menu", "help"]:
        reply = (
            "🤖 AI Assistant Menu\n\n"
            "1️⃣ Ask any question\n"
            "2️⃣ Get information\n"
            "3️⃣ Chat with AI\n"
            "4️⃣ School Demo\n\n"
            "Just send your message."
        )

    elif "school" in text:
        reply = (
            "🏫 Welcome to Thika Primary School (Demo)\n\n"
            "1️⃣ Admissions\n2️⃣ Fees\n3️⃣ Location\n4️⃣ Contact"
        )

    elif "admission" in text:
        reply = "Admissions are open. Send student name, grade, and parent contact."

    elif "fees" in text:
        reply = "Lower: $400 | Upper: $550 per term."

    elif "location" in text:
        reply = "Thika Town. 8AM - 4PM."

    else:
        try:
            if user not in memory:
                memory[user] = []

            memory[user].append(incoming_msg)
            memory[user] = memory[user][-6:]

            conversation = "\n".join(memory[user])

            response = client.models.generate_content(
                model="gemini-1.5-flash-8b",
                contents=f"Respond briefly:\n{conversation}"
            )

            reply = response.text or "Ask me anything 😊"
            memory[user].append(reply)

        except Exception as e:
            print(e)
            reply = "⚠️ AI busy. Try again."

    time.sleep(1)
    msg.body(reply)
    return str(resp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
