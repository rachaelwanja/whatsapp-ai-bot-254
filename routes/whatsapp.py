from flask import (
    Blueprint,
    request,
    redirect,
    session,
    render_template,
    Response
)

from twilio.twiml.messaging_response import MessagingResponse

from models import (
    Business,
    Service
)

from services import ask_ai

whatsapp = Blueprint(
    "whatsapp",
    __name__
)

@whatsapp.route("/whatsapp-ai")
