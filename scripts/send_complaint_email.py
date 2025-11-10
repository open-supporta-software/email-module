import asyncio
import os
import time
import datetime
import random
from email.mime.text import MIMEText
import aiosmtplib
import aioimaplib
import imaplib

# Settings
MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
MAIL_PORT = int(os.getenv("MAIL_PORT", 3025))
MAIL_IMAP_PORT = int(os.getenv("MAIL_IMAP_PORT", 3143))

CLIENT_EMAIL = "client@local.dev"
CLIENT_PASSWORD = "password1"
SUPPORT_EMAIL = "support@local.dev"

SUBJECTS = [
    "Жалоба на обслуживание",
    "Не работает личный кабинет",
    "Грубый ответ поддержки",
    "Долгое ожидание ответа",
    "Ошибка при оплате",
    "Проблема с доступом",
]

BODIES = [
    """
    Здравствуйте, служба поддержки.

    Я крайне недоволен качеством предоставляемых услуг.
    Прошу разобраться в ситуации и дать ответ в ближайшее время.

    С уважением,
    Клиент
    """,
    """
    Добрый день.

    У меня возникла проблема, которую никто не может решить уже неделю.
    Это неприемлемо! Требую срочного вмешательства.

    Клиент
    """,
    """
    Приветствую.

    Ваш сервис работает отвратительно. Постоянные сбои и ошибки.
    Когда это прекратится?

    Недовольный пользователь
    """,
    """
    Здравствуйте.

    Хочу пожаловаться на оператора, который общался со мной сегодня.
    Абсолютная некомпетентность.

    С уважением.
    """,
]


async def save_to_sent(msg_bytes):
    """Save sent email to 'Sent' folder via IMAP"""
    print("Saving copy to Sent folder...")
    try:
        client = aioimaplib.IMAP4(host=MAIL_SERVER, port=MAIL_IMAP_PORT)
        await client.wait_hello_from_server()
        await client.login(CLIENT_EMAIL, CLIENT_PASSWORD)

        # Check if Sent folder exists, create if not
        res, _ = await client.select("Sent")
        if res != "OK":
            print("Creating Sent folder...")
            await client.create("Sent")

        # Append message
        # Use imaplib to format the date
        date_time = imaplib.Time2Internaldate(time.time())
        # Signature: message_bytes, mailbox, flags, date
        await client.append(msg_bytes, "Sent", "\\Seen", date_time)

        await client.logout()
        print("✔ Saved to Sent folder")

    except Exception as e:
        print(f"✗ Failed to save to Sent: {e}")


async def send_complaint():
    subject = random.choice(SUBJECTS)
    body = random.choice(BODIES)

    print(f"Sending email from {CLIENT_EMAIL} to {SUPPORT_EMAIL}...")
    print(f"Subject: {subject}")

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = CLIENT_EMAIL
    msg["To"] = SUPPORT_EMAIL
    msg["Subject"] = subject

    try:
        # Send via SMTP
        await aiosmtplib.send(
            msg,
            hostname=MAIL_SERVER,
            port=MAIL_PORT,
            start_tls=False,
            username=CLIENT_EMAIL,
            password=CLIENT_PASSWORD,
        )
        print("✔ Email sent successfully!")

        # Save to Sent folder
        await save_to_sent(msg.as_bytes())

    except Exception as e:
        print(f"✗ Failed to send email: {e}")


if __name__ == "__main__":
    asyncio.run(send_complaint())
