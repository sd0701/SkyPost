import json
import email
import time
from threading import Thread
import requests

from bs4 import BeautifulSoup
import ssl
import certifi
import imaplib
from imapclient import IMAPClient
from elasticsearch import Elasticsearch

from transformers import pipeline
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")


es = Elasticsearch(
    ["http://localhost:9200"],
    headers={"Content-Type": "application/json"}
)


def load_accounts():
    with open("accounts.json", "r") as file:
        return json.load(file)


IMAP_ACCOUNTS = load_accounts()


def get_email_body(msg):
    #handles plain text and html
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                return part.get_payload(decode=True).decode(errors="ignore")

            elif content_type == "text/html" and "attachment" not in content_disposition:
                html_content = part.get_payload(decode=True).decode(errors="ignore")
                return BeautifulSoup(html_content, "html.parser").get_text()  # Extract text from HTML
    else:
        return msg.get_payload(decode=True).decode(errors="ignore")

    return "No content available."


def process_new_emails(account, client):
    #getting new emails
    client.select_folder("INBOX")
    messages = client.search(["SINCE", "01-Mar-2025"])  # Only categorize emails from March 1 onward

    for msg_id in messages:
        raw_message = client.fetch([msg_id], ["RFC822"])[msg_id][b"RFC822"]
        msg = email.message_from_bytes(raw_message)

        email_subject = msg["subject"] if msg["subject"] else "(No Subject)"
        email_body = get_email_body(msg)

        category = categorize_email(email_body, email_subject)
        print(f"Categorized as {category}")

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

        print(f"New email categorized as {category}: {email_subject}")

        try:
            requests.post("http://localhost:5000/trigger_update")
        except Exception as e:
            print(f"Failed to notify Flask app: {e}")


def idle_imap(account):
    #imap idle listens for new emails
    while True:
        try:
            with IMAPClient(account["host"], ssl_context=ssl.create_default_context(cafile=certifi.where())) as client:
                client.login(account["email"], account["password"])
                client.select_folder("INBOX")

                print(f"Listening for new emails in {account['email']}...")

                while True:
                    try:
                        client.idle()
                        responses = client.idle_check(timeout=60)  # Check for new emails every 60 seconds
                        client.idle_done()

                        if responses:
                            process_new_emails(account, client)

                    except imaplib.IMAP4.abort:
                        print("Connection to the server was closed unexpectedly.")
                        break  # Reconnect after breaking out of the loop
                    except Exception as e:
                        print(f"Error in IDLE loop: {e}")
                        break  # Exit the loop and attempt to reconnect

        except Exception as e:
            print(f"Error in IMAP IDLE for {account['email']}: {e}")
            time.sleep(5)  # Retry after some delay

def categorize_email(body, subject):
    #categorization using hugging face

    categories = ["Interested", "Meeting Booked", "Not Interested", "Spam", "Out of Office", "Uncategorized"]

    email_text = f"Subject: {subject}\n\n{body[:500]}"  # Limit text for processing

    try:
        result = classifier(email_text, candidate_labels=categories)
        category = result["labels"][0]

        print(f"Categorized Email: {category}")
        return category

    except Exception as e:
        print(f"Error in categorization: {e}")
        return "Uncategorized"


def fetch_old_emails(account):
    #gets old emails and categorizes them
    try:
        with IMAPClient(account["host"]) as client:
            client.login(account["email"], account["password"])
            client.select_folder("INBOX")

            messages = client.search(["SINCE", "01-Jan-2025"])  # Fetch all emails from Jan 2025 onwards

            for msg_id in messages:
                raw_message = client.fetch([msg_id], ["RFC822"])[msg_id][b"RFC822"]
                msg = email.message_from_bytes(raw_message)

                email_subject = msg["subject"] if msg["subject"] else "(No Subject)"
                email_body = get_email_body(msg)

                category = categorize_email(email_body, email_subject)

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

                print(f"Fetched old email categorized as {category}: {email_subject}")

    except Exception as e:
        print(f"Error fetching old emails for {account['email']}: {e}")

if __name__ == "__main__":
    # Fetch old emails first
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
