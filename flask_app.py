from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from elasticsearch import Elasticsearch
import json
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app)

es = Elasticsearch(["http://localhost:9200"])


def filter_recent_emails(emails):
    cutoff_date = datetime(2024, 3, 1)
    filtered = []
    for email in emails:
        try:
            email_date = datetime.strptime(email.get("date", ""), "%Y-%m-%d %H:%M:%S")
            if email_date >= cutoff_date:
                filtered.append(email)
        except ValueError:
            pass
    return filtered


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
    category = request.args.get('ai_category', '')

    # Build Elasticsearch query
    search_query = {
        "query": {
            "bool": {
                "must": [{"match": {"content": query}}] if query else [],
                "filter": []
            }
        }
    }

    if account != 'all':
        search_query["query"]["bool"]["filter"].append({"term": {"account.keyword": account}})

    if category:
        search_query["query"]["bool"]["filter"].append({"term": {"ai_category.keyword": category}})

    try:
        res = es.search(index="emails", query=search_query["query"])
        emails = [hit["_source"] for hit in res["hits"]["hits"]]
        return jsonify(emails)
    except Exception as e:
        print(f"Error searching emails: {e}")
        return jsonify({"error": "Failed to fetch emails"}), 500

@app.route('/emails', methods=['GET'])
def get_emails():
    account = request.args.get("account", "all")
    category = request.args.get("category", None)

    query_body = {"query": {"match_all": {}}} if account == "all" else {
        "query": {"match": {"account": account}}
    }
    #if the email comes under any AI category, it will be displayed when the category is selected from the sidebar
    if category and category != "inbox":
        query_body["query"] = {
            "bool": {
                "must": [query_body["query"], {"term": {"ai_category": category}}]
            }
        }
    try:
        response = es.search(index="emails", query=query_body["query"], size=1000)
        emails = [
            {**hit["_source"], "profile_image": hit["_source"].get("profile_image", "/static/profile.jpg")}
            for hit in response["hits"]["hits"]
        ]

        if category and category != "inbox":
            emails = filter_recent_emails(emails)

        return jsonify(emails)
    except Exception as e:
        print("Error fetching emails:", e)
        return jsonify({"error": "Failed to fetch emails"}), 500


@socketio.on('connect')
def handle_connect():
    print("Client connected")


@socketio.on('fetch_emails')
def fetch_emails():
    print("Fetching updated emails...")
    try:
        res = es.search(index="emails", query= {"match_all": {}}, size=1000)
        emails = [hit["_source"] for hit in res["hits"]["hits"]]
        socketio.emit('new_emails', emails)
    except Exception as e:
        print(f"Error fetching emails: {e}")


@app.route('/trigger_update', methods=['POST'])
def trigger_update():
    print("Received new email update request. Fetching latest emails...")
    try:
        res = es.search(index="emails", query={"match_all": {}}, size=1000)
        emails = [hit["_source"] for hit in res["hits"]["hits"]]
        socketio.emit('new_emails', emails)
        print(f"UI updated with {len(emails)} emails.")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Error updating UI: {e}")
        return jsonify({"error": "Failed to update UI"}), 500


if __name__ == '__main__':
    socketio.run(app, debug=True)
