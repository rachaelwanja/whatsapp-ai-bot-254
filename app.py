from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
import os
import time
import random
from datetime import datetime

app = Flask(__name__)

# Initialize Gemini client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Memory for conversations
memory = {}

# Lead storage
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

    # ---------- RESET MEMORY ----------
    if text == "reset":
        memory[user] = []
        leads[user] = {}
        reply = "🔄 Conversation reset. How can I help you today?"
        msg.body(reply)
        return str(resp)

    # ---------- GREETING ----------
    if text in ["hi", "hello", "hey"]:

        greetings = [
            "Hello 👋 I'm your AI assistant. How can I help you today?",
            "Hi there! 😊 What can I assist you with?",
            "Hey! I'm here to help. Ask me anything.",
            "Hello! 👋 How may I assist you today?"
        ]

        reply = random.choice(greetings)

    # ---------- HELP MENU ----------
    elif text in ["menu", "help"]:

        reply = (
            "🤖 AI Assistant Menu\n\n"
            "1️⃣ Ask any question\n"
            "2️⃣ Get information\n"
            "3️⃣ Chat with AI\n"
            "4️⃣ Contact support\n\n"
            "Just send your message."
        )

    # ---------- PRICE EXAMPLE ----------
    elif "price" in text:
        reply = "Prices depend on the service. Please tell me what service you're interested in."

    # ---------- LEAD CAPTURE ----------
    elif "book" in text or "service" in text:

        leads[user] = {"service": incoming_msg}
        reply = "Great! May I have your name so we can assist you better?"

    elif user in leads and "name" not in leads[user]:

        leads[user]["name"] = incoming_msg
        reply = "Thanks! Our team will contact you shortly."

    # ---------- AI CHAT ----------
    else:

        try:

            if user not in memory:
                memory[user] = []

            memory[user].append(incoming_msg)

            memory[user] = memory[user][-6:]

            conversation = "\n".join(memory[user])

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

            memory[user].append(reply)

        except Exception as e:

            print("AI ERROR:", e)

            error_text = str(e).lower()

            if "quota" in error_text or "resource_exhausted" in error_text:
                reply = "⚠️ AI is busy right now. Please try again in a minute."

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
