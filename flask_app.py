from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from elasticsearch import Elasticsearch
import json
app = Flask(__name__)
socketio = SocketIO(app)

es = Elasticsearch(["http://localhost:9200"])

@app.route('/accounts', methods=['GET'])
def get_accounts():
    with open("accounts.json", "r") as file:
        accounts = json.load(file)
    return jsonify(accounts)
@app.route('/')
def index():

    with open("accounts.json", "r") as file:
        accounts = json.load(file)

    return render_template('index.html', accounts=accounts)


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    account = request.args.get('account', 'all')

    search_body = {
        "query": {
            "bool": {
                "must": [{"match": {"content": query}}] if query else [],
                "filter": [{"term": {"account.keyword": account}}] if account != 'all' else []
            }
        }
    }

    res = es.search(index="emails", body=search_body)
    emails = [hit["_source"] for hit in res["hits"]["hits"]]
    return jsonify(emails)

@app.route('/emails', methods=['GET'])
def get_emails():
    account = request.args.get("account", "all")
    category = request.args.get("category", None)

    # Debugging print statements
    print("Requested Account:", account)
    print("Requested Category:", category)

    # Base query: Match all if account is 'all', otherwise filter by account
    query_body = {"query": {"match_all": {}}} if account == "all" else {
        "query": {"match": {"account": account}}
    }

    # Apply category filter if selected (excluding 'inbox' since it's default)
    if category and category != "inbox":
        query_body["query"] = {
            "bool": {
                "must": [query_body["query"], {"term": {"category": category}}]
            }
        }

    try:
        # Perform search in Elasticsearch
        response = es.search(index="emails", body=query_body, size=1000)
        emails = [
            {**hit["_source"], "profile_image": hit["_source"].get("profile_image", "/static/profile.jpg")}
            for hit in response["hits"]["hits"]
        ]

        # Debugging print statement
        print("Fetched Emails:", emails)

        return jsonify(emails)
    except Exception as e:
        print("Error fetching emails:", e)
        return jsonify({"error": "Failed to fetch emails"}), 500

@socketio.on('connect')
def handle_connect():
    print("Client connected")


@socketio.on('fetch_emails')
def fetch_emails():
    res = es.search(index="emails", body={"query": {"match_all": {}}})
    emails = [hit["_source"] for hit in res["hits"]["hits"]]
    socketio.emit('new_emails', emails)


if __name__ == '__main__':
    socketio.run(app, debug=True)