from brain.business_types import BUSINESS_PERSONALITIES
from brain.language import LANGUAGE
from brain.empathy import EMPATHY
from brain.booking import BOOKING
from brain.rules import RULES
from brain.personality import PERSONALITY


def build_prompt(business, services_text):
    """
    Builds the AI system prompt for a business.
    """

    business_personality = BUSINESS_PERSONALITIES.get(
        business.business_type,
        BUSINESS_PERSONALITIES["General"]
    )

    prompt = f"""
{PERSONALITY}

{LANGUAGE}

{EMPATHY}

{BOOKING}

{RULES}

{business_personality}

=================================
BUSINESS PROFILE
=================================

Business Name:
{business.business_name}

Business Type:
{business.business_type}

Location:
{business.location}

Opening Hours:
{business.opening_hours}

=================================
AVAILABLE SERVICES
=================================

{services_text}

=================================
BUSINESS INSTRUCTIONS
=================================

{business.ai_prompt}

=================================
INSTRUCTIONS
=================================

The conversation history will be provided below.

Continue naturally from where the customer left off.

Never restart the conversation.

Only ask for information that is still missing.

Never invent services.

Never invent prices.

Only use information supplied by the business.
"""

    return prompt