from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
import os

app = Flask(__name__)

# Initialize Gemini
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Memory storage for conversations
memory = {}

@app.route("/")
def home():
    return "WhatsApp AI bot running"


@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "").strip()
    user = request.values.get("From")

    resp = MessagingResponse()
    msg = resp.message()

    lower_msg = incoming_msg.lower()

    # ---------- SMART QUICK REPLIES (NO AI USED) ----------
    if lower_msg in ["hi", "hello", "hey"]:
        reply = "Hello 👋 I'm your AI assistant. Ask me anything!"

    elif lower_msg in ["help", "menu"]:
        reply = (
            "🤖 AI Assistant Menu:\n\n"
            "1️⃣ Ask any question\n"
            "2️⃣ Get information\n"
            "3️⃣ Chat with AI\n\n"
            "Just send your message."
        )

    else:

        try:

            # Initialize memory for user
            if user not in memory:
                memory[user] = []

            # Save user message
            memory[user].append({
                "role": "user",
                "content": incoming_msg
            })

            # Limit memory to last 10 messages
            memory[user] = memory[user][-10:]

            # Send conversation to Gemini
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=str(memory[user])
            )

            reply = response.text

            # Safety fallback
            if not reply:
                reply = "I'm here! Ask me something 😊"

            # Save AI response
            memory[user].append({
                "role": "assistant",
                "content": reply
            })

        except Exception as e:

            print("AI ERROR:", e)

            error_text = str(e).lower()

            # Quota error
            if "quota" in error_text or "resource_exhausted" in error_text:
                reply = "⚠️ AI is busy right now. Please try again in a minute."

            # Model error
            elif "model" in error_text:
                reply = "⚠️ AI model unavailable. Try again later."

            # General fallback
            else:
                reply = "🤖 I'm still learning. Ask me something else!"

    msg.body(reply)

    return str(resp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
