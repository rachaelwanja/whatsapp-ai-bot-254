import os
import resend


# =========================================
# RESEND CONFIG
# =========================================

resend.api_key = os.getenv(
    "RESEND_API_KEY"
)

FROM_EMAIL = os.getenv(
    "RESEND_FROM_EMAIL",
    "FlowAI <hello@flowai.co.ke>"
)


# =========================================
# SEND EMAIL
# =========================================

def send_email(to, subject, html):

    if not resend.api_key:
        raise RuntimeError(
            "RESEND_API_KEY is not configured"
        )

    params = {
        "from": FROM_EMAIL,
        "to": [to],
        "subject": subject,
        "html": html
    }

    result = resend.Emails.send(params)

    print(
        "========== RESEND EMAIL RESULT =========="
    )

    print(result)

    print(
        "========================================="
    )

    return result