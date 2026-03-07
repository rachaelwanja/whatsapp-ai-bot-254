from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai
import os

app = Flask(__name__)

# Configure Gemini API
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Correct model
model = genai.GenerativeModel("gemini-1.5-flash-latest")


@app.route("/")
def home():
    return "WhatsApp AI bot running"


@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "")

    resp = MessagingResponse()
    msg = resp.message()

    try:
        response = model.generate_content(incoming_msg)

        if response.text:
            reply = response.text
        else:
            reply = "I couldn't generate a reply."

    except Exception as e:
        print("AI ERROR:", e)
        reply = "AI error occurred."

    msg.body(reply)

    return str(resp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
