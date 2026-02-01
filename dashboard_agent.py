import os, json, time
from flask import Flask, Response, render_template_string
from kafka import KafkaConsumer, TopicPartition, KafkaAdminClient

app = Flask(__name__)
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Agent Mesh - 3 Column View</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0b0e14; color: #fff; margin: 0; padding: 20px; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 10px; }
        .lag-box { background: #1a1f29; padding: 10px 20px; border-radius: 8px; border-left: 4px solid #ff3e3e; }
        
        .dashboard-grid { 
            display: grid; 
            grid-template-columns: 1fr 1.5fr 1fr; 
            gap: 15px; 
            margin-top: 20px; 
            height: 80vh;
        }
        
        .column { background: #161b22; border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; border: 1px solid #30363d; }
        .col-header { background: #21262d; padding: 12px; font-weight: bold; text-transform: uppercase; font-size: 0.85em; letter-spacing: 1px; }
        .feed { padding: 15px; overflow-y: auto; flex-grow: 1; font-family: 'Consolas', monospace; font-size: 0.9em; }
        
        .card { background: #0d1117; border: 1px solid #30363d; padding: 12px; margin-bottom: 12px; border-radius: 6px; animation: fadeIn 0.3s ease-out; }
        .task-id { color: #58a6ff; font-size: 0.75em; margin-bottom: 5px; }
        pre { white-space: pre-wrap; word-wrap: break-word; margin: 0; color: #d1d5da; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 AI Agent Mesh <small style="color:#888; font-size:0.5em;">v2.0 (Reviewer Enabled)</small></h1>
        <div class="lag-box">SYSTEM LAG: <span id="lag-val">0</span></div>
    </div>

    <div class="dashboard-grid">
        <div class="column"><div class="col-header">🚀 Producer: Tasks</div><div class="feed" id="col-tasks"></div></div>
        <div class="column"><div class="col-header">⚙️ Consumer: Code</div><div class="feed" id="col-solutions"></div></div>
        <div class="column"><div class="col-header">🕵️ Reviewer: Critique</div><div class="feed" id="col-reviews"></div></div>
    </div>

    <script>
        const eventSource = new EventSource("/stream");
        const lagVal = document.getElementById("lag-val");

        eventSource.onmessage = function(e) {
            const data = JSON.parse(e.data);
            if (data.lag !== undefined) lagVal.innerText = data.lag;

            if (data.type === 'task') addCard('col-tasks', data.content);
            if (data.type === 'solution') addCard('col-solutions', data.content);
            if (data.type === 'review') addCard('col-reviews', data.content);
        };

        function addCard(colId, text) {
            const container = document.getElementById(colId);
            const card = document.createElement("div");
            card.className = "card";
            card.innerHTML = `<div class="task-id">${new Date().toLocaleTimeString()}</div><pre>${text}</pre>`;
            container.prepend(card);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/stream')
def stream():
    def monitor():
        admin = KafkaAdminClient(bootstrap_servers=KAFKA_BROKER, api_version=(3, 5, 0))
        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BROKER,
            api_version=(3, 5, 0),
            auto_offset_reset='latest',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        consumer.subscribe(['ai_topic', 'ai_solutions', 'ai_reviews'])
        tp = TopicPartition('ai_topic', 0)

        while True:
            msg_pack = consumer.poll(timeout_ms=500)
            
            # Calculate Lag
            try:
                end_offsets = consumer.end_offsets([tp])
                grp_offsets = admin.list_consumer_group_offsets('agent-b-group')
                lag = end_offsets[tp] - (grp_offsets[tp].offset if tp in grp_offsets else 0)
            except: lag = 0

            # Yield system lag update
            yield f"data: {json.dumps({'lag': lag})}\n\n"

            # Yield new messages
            for tp_key, messages in msg_pack.items():
                for msg in messages:
                    msg_type = 'task' if msg.topic == 'ai_topic' else ('solution' if msg.topic == 'ai_solutions' else 'review')
                    # Get the right field based on topic
                    content = msg.value.get('review') or msg.value.get('solution') or msg.value.get('task')
                    yield f"data: {json.dumps({'type': msg_type, 'content': content})}\n\n"

    return Response(monitor(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)