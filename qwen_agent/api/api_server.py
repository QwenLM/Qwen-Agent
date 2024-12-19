
import json
from flask import Flask, Response, request, jsonify


app = Flask("apiserver")


def event_stream(items):
    for item in items:
        msg = json.dumps(item, ensure_ascii=False)
        yield f'data: {msg}\n\n'
    yield f'data: [DONE]\n\n'


@app.route("/chat", methods=['POST'])
def chat():
    if not request.is_json:
        return jsonify({"status": 400}), 400
    data = request.json
    if 'messages' not in data:
        return jsonify({"status": 400}), 400
    messages = data['messages']
    stream = data.get("stream", False)
    if stream:
        return Response(event_stream(app.chat.chat(messages, stream)), mimetype='text/event-stream')
    else:
        return jsonify({"messages": list(app.chat.chat(messages, stream))}), 200


def start_apiserver(chat, server_host='0.0.0.0', server_port=8080):
    app.chat = chat
    app.run(server_host, server_port)
