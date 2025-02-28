from flask import Flask, render_template, request, jsonify
from elasticsearch import Elasticsearch
import json

app = Flask(__name__)
es = Elasticsearch(["http://localhost:9200"])


# Load IMAP accounts from JSON
def load_accounts():
    with open("accounts.json", "r") as file:
        return json.load(file)


IMAP_ACCOUNTS = load_accounts()


@app.route("/", methods=["GET"])
def index():
    """Render the search page with email accounts."""
    return render_template("index.html", accounts=IMAP_ACCOUNTS)


@app.route("/search", methods=["GET"])
def search_emails():
    """Search emails using Elasticsearch with filters."""
    query = request.args.get("q", "")
    account = request.args.get("account", "")
    folder = request.args.get("folder", "")

    filters = {"bool": {"must": []}}

    if query:
        filters["bool"]["must"].append({"match": {"body": query}})
    if account:
        filters["bool"]["must"].append({"match": {"account": account}})
    if folder:
        filters["bool"]["must"].append({"match": {"folder": folder}})

    res = es.search(index="emails", body={"query": filters})
    emails = [hit["_source"] for hit in res["hits"]["hits"]]

    return jsonify(emails)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
