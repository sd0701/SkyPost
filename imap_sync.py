import json
from imapclient import IMAPClient
from elasticsearch import Elasticsearch
import email
import time
from threading import Thread
import requests
import re
import openai
from bs4 import BeautifulSoup

import ssl
import certifi
import imaplib

openai.api_key = "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"

es = Elasticsearch(
    ["http://localhost:9200"],
    headers={"Content-Type": "application/json"}
)

def load_accounts():

    with open("accounts.json", "r") as file:
        return json.load(file)


IMAP_ACCOUNTS = load_accounts()


def get_email_body(msg):

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                return part.get_payload(decode=True).decode(errors="ignore")

            elif content_type == "text/html" and "attachment" not in content_disposition:
                html_content = part.get_payload(decode=True).decode(errors="ignore")
                return BeautifulSoup(html_content, "html.parser").get_text()
    else:
        return msg.get_payload(decode=True).decode(errors="ignore")

    return "No content available."


def process_new_emails(account, client):
    client.select_folder("INBOX")
    messages = client.search(["SINCE", "01-Mar-2025"])  # Only categorize emails from March 1 onward

    for msg_id in messages:
        raw_message = client.fetch([msg_id], ["RFC822"])[msg_id][b"RFC822"]
        msg = email.message_from_bytes(raw_message)

        email_subject = msg["subject"] if msg["subject"] else "(No Subject)"
        email_body = get_email_body(msg)

        category = categorize_email(email_body, email_subject)
        print(category)

        email_data = {
            "email_id": msg_id,
            "date": msg["date"],
            "from": msg["from"],
            "subject": email_subject,
            "folder": "inbox",
            "account": account["email"],
            "body": email_body,
            "ai_category": category
        }

        es.index(index="emails", id=msg_id, document=email_data)
        es.indices.refresh(index="emails")

        print(f" New email categorized as {category}: {email_subject}")

        try:
            requests.post("http://localhost:5000/trigger_update")
        except Exception as e:
            print(f" Failed to notify Flask app: {e}")


def idle_imap(account):
    while True:
        try:
            with IMAPClient(account["host"], ssl_context=ssl.create_default_context(cafile=certifi.where())) as client:
                client.login(account["email"], account["password"])
                client.select_folder("INBOX")

                print(f" Listening for new emails in {account['email']}...")

                while True:
                    client.idle()
                    responses = client.idle_check(timeout=60)
                    client.idle_done()

                    if responses:
                        process_new_emails(account, client)

        except Exception as e:
            print(f" Error in IMAP IDLE for {account['email']}: {e}")
            time.sleep(10)


def categorize_email(body, subject):

    prompt = f"""
    Categorize this email into one of the following:
    - Interested
    - Meeting Booked
    - Not Interested
    - Spam
    - Out of Office

    Subject: {subject}
    body: {body}

    Respond with only the category name.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
        )
        category_of_ai = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if category_of_ai:
            print(f"Categorized as: {category_of_ai}")
            return category_of_ai
        else:
            raise ValueError("Empty response from OpenAI")

    except Exception as e:
        print(f" OpenAI categorization failed: {e}")
        return "Uncategorized"

def fetch_old_emails(account):
    try:
        with IMAPClient(account["host"]) as client:
            client.login(account["email"], account["password"])
            client.select_folder("INBOX")

            messages = client.search(["SINCE", "01-Jan-2025"])  # Fetch all emails for inbox display

            for msg_id in messages:
                raw_message = client.fetch([msg_id], ["RFC822"])[msg_id][b"RFC822"]
                msg = email.message_from_bytes(raw_message)

                email_subject = msg["subject"] if msg["subject"] else "(No Subject)"
                email_body = get_email_body(msg)

                email_data = {
                    "email_id": msg_id,
                    "date": msg["date"],
                    "from": msg["from"],
                    "subject": email_subject,
                    "folder": "inbox",
                    "account": account["email"],
                    "body": email_body,
                    "ai_category": "inbox"  # Ensuring all emails appear in the inbox by default
                }

                es.index(index="emails", id=msg_id, document=email_data)
                es.indices.refresh(index="emails")
    except Exception as e:
        print(f" Error fetching old emails for {account['email']}: {e}")

if __name__ == "__main__":
    for acc in IMAP_ACCOUNTS:
        fetch_old_emails(acc)

    for acc in IMAP_ACCOUNTS:
        thread = Thread(target=idle_imap, args=(acc,))
        thread.daemon = True
        thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping IMAP Sync.")
        exit(0)
