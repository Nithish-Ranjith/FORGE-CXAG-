from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM,
    WHATSAPP_OVERRIDE_PROMPT,
)

try:
    from twilio.base.exceptions import TwilioException
    from twilio.rest import Client
except ImportError:  # pragma: no cover
    TwilioException = Exception
    Client = None


class WhatsAppAlerter:
    def __init__(self) -> None:
        self.from_ = TWILIO_WHATSAPP_FROM
        self.client = None
        if Client is not None and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    def send(self, to_number: str, message: str):
        if self.client is None:
            return None
        try:
            response = self.client.messages.create(from_=self.from_, to=to_number, body=message)
            return response.sid
        except Exception:
            return None

    def send_override_prompt(self, to_number: str):
        return self.send(to_number, WHATSAPP_OVERRIDE_PROMPT)

    def send_options_message(self, to_number: str, question: str, options: list[str]):
        option_lines = "\n".join(f"[{index + 1}] {option}" for index, option in enumerate(options))
        return self.send(to_number, f"{question}\n{option_lines}")
