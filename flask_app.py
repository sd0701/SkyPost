from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from elasticsearch import Elasticsearch

app = Flask(__name__)
socketio = SocketIO(app)


es = Elasticsearch(["http://localhost:9200"])


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    account = request.args.get('account', 'all')

    search_body = {
        "query": {
            "bool": {
                "must": [{"match": {"content": query}}] if query else [],
                "filter": [{"term": {"account": account}}] if account != 'all' else []
            }
        }
    }

    res = es.search(index="emails", body=search_body)
    emails = [hit["_source"] for hit in res["hits"]["hits"]]
    return jsonify(emails)


@app.route('/emails', methods=['GET'])
def get_emails():
    res = es.search(index="emails", body={"query": {"match_all": {}}})
    emails = [hit["_source"] for hit in res["hits"]["hits"]]
    return jsonify(emails)


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
