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

openai.api_key = ***REMOVED***

es = Elasticsearch(
    ["http://localhost:9200"],
    headers={"Content-Type": "application/json"}
)

#opening the json file
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

#processing new emails from March 1 for AI categorization
def process_new_emails(account, client):
    client.select_folder("INBOX")
    messages = client.search(["SINCE", "01-Mar-2025"])

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
        es.indices.refresh(index="emails", force=True)

        print(f" New email categorized as {category}: {email_subject}")

        try:
            requests.post("http://localhost:5000/trigger_update")
        except Exception as e:
            print(f" Failed to notify Flask app: {e}")

#for updating with new emails
def idle_imap(account):
    while True:
        try:
            with IMAPClient(account["host"]) as client:
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

#for the AI Categorization
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
        print("AI Response:", response)
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f" OpenAI categorization failed: {e}")
        return "Uncategorized"

#for getting the old emails from Jan of 2025
def fetch_old_emails(account):
    try:
        with IMAPClient(account["host"]) as client:
            client.login(account["email"], account["password"])
            client.select_folder("INBOX")

            messages = client.search(["SINCE", "01-Jan-2025"])

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
                    "ai_category": "inbox"
                }

                es.index(index="emails", id=msg_id, document=email_data)
                es.indices.refresh(index="emails")
    except Exception as e:
        print(f" Error fetching old emails for {account['email']}: {e}")

#main part of code
if __name__ == "__main__":
    for acc in IMAP_ACCOUNTS:
        fetch_old_emails(acc)

    for acc in IMAP_ACCOUNTS:
        thread = Thread(target=idle_imap, args=(acc,))
        thread.daemon = True
        thread.start()

    while True:
        time.sleep(1)
