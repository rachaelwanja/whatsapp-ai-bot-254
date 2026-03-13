from flask import Flask, request, jsonify, send_file
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
import os
import random
from datetime import datetime

app = Flask(__name__)

# Gemini AI client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Memory storage
memory = {}

# Lead storage
leads = {}

# ---------------------------
# Home Route
# ---------------------------
@app.route("/")
def home():
    return "WhatsApp AI bot running"


# ---------------------------
# Web Chat Page
# ---------------------------
@app.route("/webchat")
def webchat():
    return send_file("chat.html")


# ---------------------------
# Web Chat API
# ---------------------------
@app.route("/chat", methods=["POST"])
def chat():

    data = request.json
    user_message = data.get("message", "")

    try:

        response = client.models.generate_content(
            model="gemini-1.5-flash-8b",
            contents=user_message
        )

        reply = response.text

    except Exception as e:
        print("AI ERROR:", e)
        reply = "AI is currently busy. Please try again."

    return jsonify({"reply": reply})


# ---------------------------
# WhatsApp Bot
# ---------------------------
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "").strip()
    user = request.values.get("From")

    resp = MessagingResponse()
    msg = resp.message()

    text = incoming_msg.lower()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Log user message
    with open("chat_log.txt", "a") as log:
        log.write(f"{timestamp} | {user} | USER: {incoming_msg}\n")


    # Reset conversation
    if text == "reset":
        memory[user] = []
        leads[user] = {}
        reply = "🔄 Conversation reset. How can I help you today?"
        msg.body(reply)
        return str(resp)


    # Greeting responses
    if text in ["hi", "hello", "hey"]:

        greetings = [
            "Hello 👋 I'm your AI assistant. How can I help you today?",
            "Hi there! 😊 What can I assist you with?",
            "Hey! I'm here to help. Ask me anything.",
            "Hello! 👋 How may I assist you today?"
        ]

        reply = random.choice(greetings)


    # Help menu
    elif text in ["menu", "help"]:

        reply = (
            "🤖 AI Assistant Menu\n\n"
            "1️⃣ Ask any question\n"
            "2️⃣ Get information\n"
            "3️⃣ Chat with AI\n"
            "4️⃣ Book a service\n\n"
            "Just send your message."
        )


    # Price question
    elif "price" in text:
        reply = "Prices depend on the service. Tell me what you need and I’ll help."


    # Lead capture
    elif "book" in text or "service" in text:

        leads[user] = {"service": incoming_msg}

        reply = "Great! May I have your name so we can assist you better?"


    elif user in leads and "name" not in leads[user]:

        leads[user]["name"] = incoming_msg

        reply = "Thanks! Our team will contact you shortly."


    # AI conversation
    else:

        try:

            if user not in memory:
                memory[user] = []

            memory[user].append(incoming_msg)

            # Keep last 6 messages
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
                reply = "⚠️ AI is busy right now. Please try again later."

            elif "model" in error_text:
                reply = "⚠️ AI model unavailable."

            else:
                reply = "🤖 I'm still learning. Ask another question."


    # Log bot reply
    with open("chat_log.txt", "a") as log:
        log.write(f"{timestamp} | BOT: {reply}\n")

    msg.body(reply)

    return str(resp)


# ---------------------------
# Run Server
# ---------------------------
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(host="0.0.0.0", port=port)
