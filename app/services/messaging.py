"""
Serwis wysyłki wiadomości: WhatsApp (Twilio) + Viber (placeholder) + Email (placeholder)
"""
import os
from twilio.rest import Client as TwilioClient

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")  # sandbox default
_twilio = None


def get_twilio():
    global _twilio
    if _twilio is None:
        _twilio = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
    return _twilio


def build_schedule_link(token: str) -> str:
    base = os.getenv("BASE_URL", "http://localhost:8000")
    print(f"[BASE_URL] Using: {base}")
    return f"{base}/schedule/{token}"


def render_template(body: str, employee, month_name: str, token: str) -> str:
    return (
        body
        .replace("{first_name}", employee.first_name)
        .replace("{last_name}", employee.last_name)
        .replace("{month_name}", month_name)
        .replace("{schedule_link}", build_schedule_link(token))
    )


async def send_whatsapp(to_phone: str, message: str) -> dict:
    """
    Wysyła wiadomość WhatsApp przez Twilio.
    to_phone format: +48XXXXXXXXX
    """
    print(f"[WHATSAPP] Sending to {to_phone} from {TWILIO_WHATSAPP_FROM}")
    print(f"[WHATSAPP] SID: {TWILIO_SID[:8] if TWILIO_SID else 'MISSING'}...")
    try:
        client = get_twilio()
        msg = client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_FROM,
            to=f"whatsapp:{to_phone}",
        )
        print(f"[WHATSAPP] Success: {msg.sid}")
        return {"status": "sent", "external_id": msg.sid}
    except Exception as e:
        print(f"[WHATSAPP] ERROR: {e}")
        return {"status": "failed", "error": str(e)}


async def send_viber(to_phone: str, message: str) -> dict:
    """Placeholder — Viber API do zintegrowania później."""
    return {"status": "failed", "error": "Viber not configured yet"}


async def send_email(to_email: str, subject: str, message: str) -> dict:
    """Placeholder — SMTP/SendGrid do zintegrowania później."""
    return {"status": "failed", "error": "Email not configured yet"}


MONTH_NAMES_PL = {
    1: "styczeń", 2: "luty", 3: "marzec", 4: "kwiecień",
    5: "maj", 6: "czerwiec", 7: "lipiec", 8: "sierpień",
    9: "wrzesień", 10: "październik", 11: "listopad", 12: "grudzień",
}
