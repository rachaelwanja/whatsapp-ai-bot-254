from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
import os

app = Flask(__name__)

# Initialize Gemini client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route("/")
def home():
    return "WhatsApp AI bot running"


@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "").strip()

    resp = MessagingResponse()
    msg = resp.message()

    try:
        # Call Gemini AI
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=incoming_msg
        )

        reply = response.text

        # Safety check if Gemini returns nothing
        if not reply:
            reply = "I'm here! How can I help you?"

    except Exception as e:

        print("AI ERROR:", e)

        error_text = str(e).lower()

        # QUOTA LIMIT
        if "quota" in error_text or "resource_exhausted" in error_text:
            reply = "⚠️ AI is busy right now. Please try again in a minute."

        # MODEL ERROR
        elif "model" in error_text:
            reply = "⚠️ AI model unavailable. Try again later."

        # GENERAL ERROR
        else:
            reply = "🤖 I'm still learning. Ask me something else!"

    msg.body(reply)

    return str(resp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
