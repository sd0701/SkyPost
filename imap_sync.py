import json
from imapclient import IMAPClient
from elasticsearch import Elasticsearch
import email
import time
from threading import Thread

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

        email_data = {
            "email_id": msg_id,
            "date": msg["date"],
            "from": msg["from"],
            "subject": msg["subject"],
            "folder": "INBOX",
            "account": account["email"],
            "body": get_email_body(msg)
        }

        es.index(index="emails", body=email_data)
        print(f"📩 New email indexed: {msg['subject']} from {msg['from']}")


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


if __name__ == "__main__":

    for acc in IMAP_ACCOUNTS:
        thread = Thread(target=idle_imap, args=(acc,))
        thread.daemon = True
        thread.start()

    while True:
        time.sleep(1)
