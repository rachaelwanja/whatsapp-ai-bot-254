from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "WhatsApp AI Bot is running successfully!"

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip()

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": incoming_msg}
        ]
    )

    reply = response.choices[0].message.content

    twilio_response = MessagingResponse()
    twilio_response.message(reply)

    return str(twilio_response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
