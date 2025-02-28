import json
from imapclient import IMAPClient
from elasticsearch import Elasticsearch
import email

es = Elasticsearch(
    ["http://localhost:9200"],
    headers={"Content-Type": "application/json"}
)

def load_accounts():
    with open("accounts.json", "r") as file:
        return json.load(file)

IMAP_ACCOUNTS = load_accounts()

def connect_imap(account):

    try:
        with IMAPClient(account["host"]) as client:
            client.login(account["email"], account["password"])
            client.select_folder("INBOX")
            print(f"Connected to {account['email']} successfully!")

            # Fetch recent emails (last 30 days)
            messages = client.search("SINCE 30-Oct-2023")
            print(f"{len(messages)} emails found in {account['email']}")

            for msg_id in messages[:5]:
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
                print(f"Indexed Email {msg_id} into Elasticsearch!")

            client.logout()
    except Exception as e:
        print(f"IMAP connection error for {account['email']}: {e}")

def get_email_body(msg):

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(errors="ignore")
    else:
        return msg.get_payload(decode=True).decode(errors="ignore")

    return "No content"

def search_emails(query="", account=None, folder=None):

    filters = {"bool": {"must": []}}

    if query:
        filters["bool"]["must"].append({"match": {"body": query}})
    if account:
        filters["bool"]["must"].append({"match": {"account": account}})
    if folder:
        filters["bool"]["must"].append({"match": {"folder": folder}})

    res = es.search(index="emails", body={"query": filters})
    print(res["hits"]["hits"])

if __name__ == "__main__":
    for acc in IMAP_ACCOUNTS:
        connect_imap(acc)

#done