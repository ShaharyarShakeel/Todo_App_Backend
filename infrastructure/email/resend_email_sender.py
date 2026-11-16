import logging
import smtplib
import ssl
from datetime import date
from html import escape
from email.message import EmailMessage
from email.utils import formataddr

from application.ports.email_sender import EmailSender

logger = logging.getLogger(__name__)


class ResendEmailSender(EmailSender):
    """Uses Resend for its allowed test recipient and Gmail SMTP otherwise."""

    def __init__(
        self,
        api_key: str,
        from_email: str,
        allowed_resend_recipient: str = "",
        gmail_address: str = "",
        gmail_app_password: str = "",
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
    ):
        self.api_key = api_key.strip()
        self.from_email = from_email.strip()
        self.allowed_resend_recipient = allowed_resend_recipient.strip().lower()
        self.gmail_address = gmail_address.strip()
        self.gmail_app_password = gmail_app_password.strip().replace(" ", "")
        self.smtp_server = smtp_server.strip()
        self.smtp_port = int(smtp_port)

    def send_welcome_email(self, email: str) -> None:
        if self._can_use_resend_for(email):
            try:
                import resend

                resend.api_key = self.api_key
                response = resend.Emails.send(
                    {
                        "from": self.from_email,
                        "to": [email],
                        "subject": "Welcome to Todo App",
                        "text": (
                            "Welcome to Todo App! Your account is ready. "
                            "You can now sign in and start organizing your tasks."
                        ),
                        "html": (
                            "<h1>Welcome to Todo App!</h1>"
                            "<p>Your account is ready. You can now sign in and start "
                            "organizing your tasks.</p>"
                        ),
                    }
                )
                logger.info(
                    "Resend accepted welcome email; message_id=%s", response.get("id")
                )
                return
            except Exception as error:
                logger.warning(
                    "Resend could not send the welcome email (%s); trying Gmail SMTP.",
                    type(error).__name__,
                )
        else:
            logger.info(
                "Recipient is outside the configured Resend test recipient; "
                "using Gmail SMTP."
            )

        self._send_with_gmail_smtp(email)

    def send_todo_reminder_email(
        self, email: str, title: str, due_date: date
    ) -> None:
        """Send Todo reminders directly by Gmail SMTP, never through Resend."""
        safe_title = escape(title)
        date_text = due_date.isoformat()
        message = EmailMessage()
        message["From"] = formataddr(("Todo App", self.gmail_address))
        message["To"] = email
        message["Subject"] = "Todo due-date reminder"
        message.set_content(
            f'Reminder: "{title}" is due on {date_text}.'
        )
        message.add_alternative(
            f"<h1>Todo reminder</h1><p><strong>{safe_title}</strong> is due on "
            f"<strong>{date_text}</strong>.</p>",
            subtype="html",
        )
        self._send_message_with_gmail_smtp(message)

    def _can_use_resend_for(self, email: str) -> bool:
        if not self.api_key or not self.from_email:
            return False
        return (
            not self.allowed_resend_recipient
            or email.strip().lower() == self.allowed_resend_recipient
        )

    def _send_with_gmail_smtp(self, email: str) -> None:
        if not self.gmail_address or not self.gmail_app_password:
            raise RuntimeError(
                "GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be configured "
                "to use the Gmail SMTP fallback."
            )

        message = EmailMessage()
        message["From"] = formataddr(("Todo App", self.gmail_address))
        message["To"] = email
        message["Subject"] = "Welcome to Todo App"
        message.set_content(
            "Welcome to Todo App! Your account is ready. "
            "You can now sign in and start organizing your tasks."
        )
        message.add_alternative(
            "<h1>Welcome to Todo App!</h1>"
            "<p>Your account is ready. You can now sign in and start "
            "organizing your tasks.</p>",
            subtype="html",
        )

        self._send_message_with_gmail_smtp(message)

    def _send_message_with_gmail_smtp(self, message: EmailMessage) -> None:
        if not self.gmail_address or not self.gmail_app_password:
            raise RuntimeError(
                "GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be configured "
                "to use Gmail SMTP."
            )

        context = ssl.create_default_context()
        if self.smtp_port == 465:
            with smtplib.SMTP_SSL(
                self.smtp_server, self.smtp_port, context=context, timeout=20
            ) as smtp:
                smtp.login(self.gmail_address, self.gmail_app_password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=20) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                smtp.login(self.gmail_address, self.gmail_app_password)
                smtp.send_message(message)

        logger.info("Gmail SMTP accepted email for delivery.")
