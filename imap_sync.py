from imapclient import IMAPClient

# List of IMAP accounts
IMAP_ACCOUNTS = [
    {
        "host": "imap.gmail.com", # Gmail IMAP host
        "email": "sivadharshini0107@gmail.com",
        "password": "fxbk cmdx psah ounl"
    }
]

def connect_imap(account):
    """ Connect to an IMAP account and fetch recent emails """
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
