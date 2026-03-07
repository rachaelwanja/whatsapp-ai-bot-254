from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai
import os

app = Flask(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing. Add it in Render Environment Variables.")

genai.configure(api_key=GEMINI_API_KEY)

# Load Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")


@app.route("/", methods=["GET"])
def home():
    return "✅ WhatsApp AI Bot is running!"


@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "").strip()

    resp = MessagingResponse()
    msg = resp.message()

    try:
        # Generate AI response
        ai_response = model.generate_content(incoming_msg)

        # Safe extraction of response text
        if ai_response and ai_response.candidates:
            reply = ai_response.candidates[0].content.parts[0].text
        else:
            reply = "I couldn't generate a response."

    except Exception as e:
        print("AI ERROR:", e)
        reply = "⚠️ AI failed to respond."

    msg.body(reply)

    return str(resp)


if __name__ == "__main__":
