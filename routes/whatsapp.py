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
    db,
    Business,
    Service,
    Conversation
)

from services import ask_ai

from brain.personality import PERSONALITY
from brain.language import LANGUAGE
from brain.empathy import EMPATHY
from brain.booking import BOOKING
from brain.rules import RULES
from brain.business_types import BUSINESS_PERSONALITIES

whatsapp = Blueprint(
    "whatsapp",
    __name__
)

# =========================================
# WHATSAPP AI PAGE
# =========================================

@whatsapp.route("/whatsapp-ai")
def whatsapp_ai():

    if "business_id" not in session:
        return redirect("/login")

    business = Business.query.get(
        session["business_id"]
    )

    return render_template(
        "whatsapp_ai.html",
        business=business
    )
