import asyncio
import email
from email.header import decode_header
import os
import aioimaplib

# IMAP settings
MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
MAIL_IMAP_PORT = int(os.getenv("MAIL_IMAP_PORT", 3143))
MAIL_USERNAME = "support@local.dev"
MAIL_PASSWORD = "password2"


def decode_mime_words(s):
    """Decode MIME encoded words in email headers"""
    if s is None:
        return ""
    decoded = decode_header(s)
    return " ".join(
        str(part, encoding or "utf-8") if isinstance(part, bytes) else part
        for part, encoding in decoded
    )


async def get_emails(folder="INBOX"):
    print(f"Connecting to {MAIL_SERVER}:{MAIL_IMAP_PORT} as {MAIL_USERNAME}...")

    try:
        client = aioimaplib.IMAP4(host=MAIL_SERVER, port=MAIL_IMAP_PORT)
        await client.wait_hello_from_server()

        await client.login(MAIL_USERNAME, MAIL_PASSWORD)

        # Select folder
        print(f"📁 Checking folder: {folder}")
        res, data = await client.select(folder)
        if res != "OK":
            print(f"✗ Folder {folder} not found or error: {res}")
            await client.logout()
            return

        # Search for all emails
        res, data = await client.search("ALL")
        if res != "OK":
            print("✗ No emails found or search error")
            await client.logout()
            return

        msg_nums = data[0].split()

        if not msg_nums:
            print("  (No emails in this folder)")

        for num in msg_nums:
            res, data = await client.fetch(num.decode(), "(RFC822)")
            if res != "OK":
                continue

            raw_email = data[1]
            msg = email.message_from_bytes(raw_email)

            subject = decode_mime_words(msg.get("Subject", "No Subject"))
            from_ = decode_mime_words(msg.get("From", "Unknown"))
            to = decode_mime_words(msg.get("To", "Unknown"))
            date = msg.get("Date", "Unknown")

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        try:
                            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")  # pyright: ignore[reportAttributeAccessIssue]
                        except:
                            body = part.get_payload()
                        break
            else:
                try:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")  # pyright: ignore[reportAttributeAccessIssue]
                except:
                    body = msg.get_payload()

            print(f"\n  ┌─ ID: {num.decode()}")
            print(f"  ├─ From: {from_}")
            print(f"  ├─ To: {to}")
            print(f"  ├─ Subject: {subject}")
            print(f"  ├─ Date: {date}")
            print(f"  └─ Body: {body.strip()[:100]}...")  # pyright: ignore[reportAttributeAccessIssue]

        await client.logout()

    except Exception as e:
        print(f"✗ Error: {e}")


async def main():
    print("=== Reading Support Emails ===")
    await get_emails("INBOX")
    print("\n")
    await get_emails("Sent")


if __name__ == "__main__":
    asyncio.run(main())
