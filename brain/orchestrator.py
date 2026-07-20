from brain.prompt_builder import build_prompt
from services import ask_ai


def handle_message(business, services_text, history):
    """
    FlowAI Brain Orchestrator (Version 1)

    Responsibilities:
    - Build the AI prompt
    - Combine it with conversation history
    - Ask the AI
    - Return the reply
    """

    prompt = build_prompt(
        business=business,
        services_text=services_text
    )

    messages = [
        {
            "role": "system",
            "content": prompt
        }
    ]

    messages.extend(history)

    reply = ask_ai(messages)

    return reply