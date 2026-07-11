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

from FlowAI.brain.personality import PERSONALITY
from FlowAI.brain.language import LANGUAGE
from FlowAI.brain.empathy import EMPATHY
from FlowAI.brain.booking import BOOKING
from FlowAI.brain.rules import RULES
from FlowAI.brain.business_types import BUSINESS_PERSONALITIES

whatsapp = Blueprint(
    "whatsapp",
    __name__
)
