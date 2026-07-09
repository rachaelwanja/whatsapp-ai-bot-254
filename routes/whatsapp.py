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

# =========================================
# WHATSAPP AI
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
    
