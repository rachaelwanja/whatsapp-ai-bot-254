@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    from flask import request
    from twilio.twiml.messaging_response import MessagingResponse
    from openai import OpenAI
    import os

    incoming_msg = request.form.get("Body", "").strip()

    # Prevent crash during Twilio validation
    if not incoming_msg:
        return str(MessagingResponse())

    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful WhatsApp AI assistant."},
                {"role": "user", "content": incoming_msg}
            ]
        )

        reply = response.choices[0].message.content

    except Exception as e:
        reply = "Sorry, something went wrong."

    twilio_response = MessagingResponse()
    twilio_response.message(reply)

    return str(twilio_response)
