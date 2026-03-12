from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
import os
import time
import random
from datetime import datetime

app = Flask(__name__)

# Gemini client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Memory storage
memory = {}

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

    # ---------- LOG USER MESSAGE ----------
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open("chat_log.txt", "a") as log:
        log.write(f"{timestamp} | {user} | USER: {incoming_msg}\n")

    # ---------- RESET MEMORY ----------
    if text == "reset":
        memory[user] = []
        reply = "🔄 Conversation memory cleared. Let's start again!"
        msg.body(reply)
        return str(resp)

    # ---------- HUMAN GREETINGS ----------
    if text in ["hi", "hello", "hey"]:

        greetings = [
            "Hello 👋 I'm your AI assistant. How can I help you today?",
            "Hi there! 😊 What can I help you with?",
            "Hey! I'm here to help. Ask me anything.",
            "Hello! 👋 How can I assist you today?"
        ]

        reply = random.choice(greetings)

    elif text in ["menu", "help"]:

        reply = (
            "🤖 AI Assistant Menu\n\n"
            "1️⃣ Ask any question\n"
            "2️⃣ Get explanations\n"
            "3️⃣ Chat with AI\n\n"
            "Just send your message."
        )

    elif "price" in text:

        reply = "Prices depend on the service. Please ask what you need."

    else:

        try:

            if user not in memory:
                memory[user] = []

            # Save user message
            memory[user].append(incoming_msg)

            # Limit memory
            memory[user] = memory[user][-6:]

            conversation = "\n".join(memory[user])

            # AI request
            response = client.models.generate_content(
                model="gemini-1.5-flash-8b",
                contents=f"""
You are a helpful WhatsApp AI assistant.
Respond clearly and briefly.

Conversation:
{conversation}
"""
            )

            reply = response.text

            if not reply:
                reply = "I'm here 😊 Ask me something."

            # Save AI reply
            memory[user].append(reply)

        except Exception as e:

            print("AI ERROR:", e)

            error_text = str(e).lower()

            if "quota" in error_text or "resource_exhausted" in error_text:
                reply = "⚠️ AI is busy right now. Try again in a minute."

            elif "model" in error_text:
                reply = "⚠️ AI model unavailable."

            else:
                reply = "🤖 I'm still learning. Ask another question."

    # ---------- LOG BOT REPLY ----------
    with open("chat_log.txt", "a") as log:
        log.write(f"{timestamp} | BOT: {reply}\n")

    # ---------- HUMAN RESPONSE DELAY ----------
    time.sleep(2)

    msg.body(reply)

    return str(resp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
