import json
from imapclient import IMAPClient
from elasticsearch import Elasticsearch
import email
import time
from threading import Thread

import re
import openai

OPENAI_API_KEY = "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
"

es = Elasticsearch(
    ["http://localhost:9200"],
    headers={"Content-Type": "application/json"},
    request_timeout=30
)


def load_accounts():

    with open("accounts.json", "r") as file:
        return json.load(file)


IMAP_ACCOUNTS = load_accounts()


def get_email_body(msg):

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html":
                return part.get_payload(decode=True).decode(errors="ignore")
    else:
        return msg.get_payload(decode=True).decode(errors="ignore")

    return "No content available."

def process_new_emails(account, client):
    client.select_folder("INBOX")
    messages = client.search("UNSEEN")

    for msg_id in messages:
        raw_message = client.fetch([msg_id], ["RFC822"])[msg_id][b"RFC822"]
        msg = email.message_from_bytes(raw_message)

        email_body = get_email_body(msg)
        email_subject = msg["subject"]

        # 🔥 Categorize the email
        category = categorize_email(email_body, email_subject)

        email_data = {
            "email_id": msg_id,
            "date": msg["date"],
            "from": msg["from"],
            "subject": email_subject,
            "folder": "INBOX",
            "account": account["email"],
            "body": email_body,
            "category": category  # Store category in Elasticsearch
        }

        es.index(index="emails", body=email_data)
        print(f"📩 New email categorized as {category}: {email_subject}")

def idle_imap(account):

    while True:
        try:
            with IMAPClient(account["host"]) as client:
                client.login(account["email"], account["password"])
                client.select_folder("INBOX")

                print(f"🔄 Listening for new emails in {account['email']}...")

                while True:
                    client.idle()
                    client.idle_check(timeout=60)
                    client.idle_done()


                    process_new_emails(account, client)

        except Exception as e:
            print(f"❌ Error in IMAP IDLE for {account['email']}: {e}")
            time.sleep(10)

def categorize_email(body, subject):
    """Uses AI to categorize emails into predefined categories."""
    prompt = f"""
    Categorize this email into one of the following:
    - Interested
    - Meeting Booked
    - Not Interested
    - Spam
    - Out of Office

    Subject: {subject}
    Body: {body}

    Respond with only the category name.
    """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        api_key=OPENAI_API_KEY  # Use the API key here
    )

    return response["choices"][0]["message"]["content"].strip()

if __name__ == "__main__":

    for acc in IMAP_ACCOUNTS:
        thread = Thread(target=idle_imap, args=(acc,))
        thread.daemon = True
        thread.start()

    while True:
        time.sleep(1)