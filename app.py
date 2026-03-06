from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai
import os

app = Flask(__name__)

# Load Gemini API key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-pro")

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip()

    resp = MessagingResponse()
    msg = resp.message()

    try:
        response = model.generate_content(incoming_msg)
        reply = response.text
    except Exception as e:
        print(e)
        reply = "Sorry, AI error."

    msg.body(reply)

    return str(resp)

if __name__ == "__main__":
    app.run()
