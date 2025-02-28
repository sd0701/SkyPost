import json
from imapclient import IMAPClient

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

            client.logout()
    except Exception as e:
        print(f"IMAP connection error for {account['email']}: {e}")

if __name__ == "__main__":
    for acc in IMAP_ACCOUNTS:
        connect_imap(acc)
#done