import os
import mimetypes
import smtplib
from email.message import EmailMessage

from config import (
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_SENDER,
    SMTP_USERNAME,
    SMTP_USE_TLS,
)


def send_email(to_email: str, subject: str, body: str, html_body: str = None, attachments: list[str] = None) -> None:
    if not to_email:
        raise ValueError("Recipient email is required.")
    if not SMTP_HOST:
        raise ValueError("SMTP_HOST is not configured.")
    if not SMTP_SENDER:
        raise ValueError("SMTP_SENDER or SMTP_USERNAME is not configured.")

    message = EmailMessage()
    message["From"] = SMTP_SENDER
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    if attachments:
        for filepath in attachments:
            if not filepath or not os.path.exists(filepath):
                continue
            
            # Guess the content type based on the file extension
            ctype, encoding = mimetypes.guess_type(filepath)
            if ctype is None or encoding is not None:
                # Default to a generic octet-stream binary type
                ctype = "application/octet-stream"
            
            maintype, subtype = ctype.split("/", 1)
            
            # Read file in binary mode
            with open(filepath, "rb") as f:
                file_data = f.read()
                file_name = os.path.basename(filepath)
                
            message.add_attachment(
                file_data,
                maintype=maintype,
                subtype=subtype,
                filename=file_name
            )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        if SMTP_USE_TLS:
            smtp.starttls()
        if SMTP_USERNAME:
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(message)


