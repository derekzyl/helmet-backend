import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, List

from fastapi import BackgroundTasks, HTTPException, status
from jinja2 import DictLoader, Environment
from pydantic import EmailStr

from app.config import env
from app.utils.logger import log
from app.utils.mail.templates import EMAIL_TEMPLATES


class EmailTemplateTypesEnum(str, Enum):
    VERIFY_EMAIL = "verify_email"
    RESET_PASSWORD = "reset_password"
    PASSWORD_CHANGE = "password_change"
    WELCOME = "welcome"


class SMTPMailer:
    def __init__(
        self,
        background_tasks: BackgroundTasks,
        receiver_emails: List[EmailStr],
        template_name: EmailTemplateTypesEnum,
        subject: str,
        template_data: dict[str, Any],
        background: bool = False,
    ):
        self.sender_email: EmailStr = env.env["mail"]["mail_sender"]
        self.sender_password = env.env["mail"]["mail_password"]
        self.smtp_server = env.env["mail"]["mail_server"]
        self.smtp_port = env.env["mail"]["mail_port"]
        self.background = background
        self.background_tasks = background_tasks
        self.receiver_emails = receiver_emails
        self.subject = subject
        self.template_name = template_name
        self.template_data = template_data

    def _get_html_content(self) -> str:
        template_env = Environment(loader=DictLoader(EMAIL_TEMPLATES))
        template = template_env.get_template(self.template_name.value)
        return template.render(**self.template_data)

    def _create_message(self, receiver_email: str) -> MIMEMultipart:
        message = MIMEMultipart("alternative")
        message["Subject"] = self.subject
        message["From"] = self.sender_email
        message["To"] = receiver_email
        message.attach(MIMEText(self._get_html_content(), "html"))
        return message

    def _send_sync(self) -> None:
        context = ssl.create_default_context()
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            if env.env["mail"].get("mail_use_tls", True):
                server.starttls(context=context)
            if env.env["mail"].get("use_credentials", True):
                server.login(self.sender_email, self.sender_password)
            for receiver in self.receiver_emails:
                server.sendmail(
                    self.sender_email,
                    receiver,
                    self._create_message(receiver).as_string(),
                )

    async def send_mail(self) -> None:
        try:
            if self.background:
                self.background_tasks.add_task(self._send_sync)
            else:
                self._send_sync()
        except Exception as exc:
            log.logs.error(f"Failed to send email: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email",
            )
