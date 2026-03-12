from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
import os
import random

app = Flask(__name__)

# -----------------------------
# Gemini AI Setup
# -----------------------------
client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY")
)

# -----------------------------
# Memory Storage
# -----------------------------
memory = {}

# -----------------------------
# Lead Storage
# -----------------------------
leads = {}

# -----------------------------
# Home Route (Render health check)
# -----------------------------
@app.route("/")
def home():
    return "WhatsApp AI Bot Running"


# -----------------------------
# WhatsApp Webhook
# -----------------------------
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "")
    incoming_msg = incoming_msg.strip()

    user = request.values.get("From")

    resp = MessagingResponse()
    msg = resp.message()

    text = incoming_msg.lower()

    # -----------------------------
    # Reset conversation
    # -----------------------------
    if text == "reset":
        memory[user] = []
        leads[user] = {}
        reply = "🔄 Conversation reset. How can I help you today?"
        msg.body(reply)
        return str(resp)

    # -----------------------------
    # Greeting
    # -----------------------------
    if text in ["hi", "hello", "hey"]:

        greetings = [
            "Hello 👋 I'm your AI assistant. How can I help you today?",
            "Hi there 😊 What can I assist you with?",
            "Hey! I'm here to help. Ask me anything.",
            "Hello! How may I assist you today?"
        ]

        reply = random.choice(greetings)

    # -----------------------------
    # Help menu
    # -----------------------------
    elif text in ["menu", "help"]:

        reply = (
            "🤖 AI Assistant Menu\n\n"
            "1️⃣ Ask any question\n"
            "2️⃣ Get information\n"
            "3️⃣ Chat with AI\n"
            "4️⃣ Book a service\n\n"
            "Just send your message."
        )

    # -----------------------------
    # Price example
    # -----------------------------
    elif "price" in text:

        reply = "Prices depend on the service. Please tell me what service you need."

    # -----------------------------
    # Lead capture
    # -----------------------------
    elif "book" in text or "service" in text:

        leads[user] = {"service": incoming_msg}

        reply = "Great! May I have your name so we can assist you better?"

    elif user in leads and "name" not in leads[user]:

        leads[user]["name"] = incoming_msg

        reply = "Thank you! Our team will contact you shortly."

    # -----------------------------
    # AI Chat
    # -----------------------------
    else:

        try:

            if user not in memory:
                memory[user] = []

            memory[user].append(incoming_msg)

            # keep last 6 messages
            memory[user] = memory[user][-6:]

            conversation = "\n".join(memory[user])

            response = client.models.generate_content(
                model="gemini-2.0-flash",
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

            if "quota" in error_text:
                reply = "⚠️ AI is busy right now. Please try again shortly."

            elif "model" in error_text:
                reply = "⚠️ AI model unavailable."

            else:
                reply = "🤖 I'm still learning. Ask another question."

    msg.body(reply)

    return str(resp)


# -----------------------------
# Run Flask
# -----------------------------
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
