from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
import os

app = Flask(__name__)

# Gemini client
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

@app.route("/")
def home():
    return "WhatsApp AI Bot Running"

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "")

    resp = MessagingResponse()
    msg = resp.message()

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=incoming_msg
        )

        reply = response.text

    except Exception as e:
        print("AI ERROR:", e)
        reply = "AI error occurred."

    msg.body(reply)

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
