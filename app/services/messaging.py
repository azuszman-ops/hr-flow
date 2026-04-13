"""
Serwis wysyłki wiadomości: WhatsApp (Meta Cloud API) + Viber (placeholder) + Email (placeholder)
"""
import os
import httpx

META_ACCESS_TOKEN = os.getenv("META_WHATSAPP_TOKEN")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
META_API_URL = "https://graph.facebook.com/v20.0"


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


def _normalize_phone(phone: str) -> str:
    """Usuwa + z numeru telefonu (Meta API wymaga E.164 bez +)."""
    return phone.lstrip("+")


async def send_whatsapp(to_phone: str, message: str) -> dict:
    """
    Wysyła wiadomość WhatsApp przez Meta Cloud API.
    to_phone format: +48XXXXXXXXX
    """
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        print("[WHATSAPP] ERROR: META_WHATSAPP_TOKEN or META_PHONE_NUMBER_ID not set")
        return {"status": "failed", "error": "Meta API not configured"}

    phone = _normalize_phone(to_phone)
    print(f"[WHATSAPP] Sending to {phone} via Meta Cloud API")

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message},
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{META_API_URL}/{META_PHONE_NUMBER_ID}/messages",
                headers={
                    "Authorization": f"Bearer {META_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
        data = resp.json()
        if resp.status_code == 200:
            msg_id = data.get("messages", [{}])[0].get("id", "")
            print(f"[WHATSAPP] Success: {msg_id}")
            return {"status": "sent", "external_id": msg_id}
        else:
            error = data.get("error", {}).get("message", str(data))
            print(f"[WHATSAPP] ERROR {resp.status_code}: {error}")
            return {"status": "failed", "error": error}
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
