from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai
import os

app = Flask(__name__)

# Configure Gemini AI
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-pro")


@app.route("/")
def home():
    return "WhatsApp AI Bot is running!"


@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip()

    try:
        # Generate AI response
        response = model.generate_content(incoming_msg)
        reply = response.text

    except Exception as e:
        reply = "Sorry, something went wrong."

    # Send reply to WhatsApp
    twilio_response = MessagingResponse()
    twilio_response.message(reply)

    return str(twilio_response)


if __name__ == "__main__":
    app.run()
