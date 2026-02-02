import os, json, time
from flask import Flask, Response, render_template_string
from kafka import KafkaConsumer, TopicPartition, KafkaAdminClient

app = Flask(__name__)
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Agent Mesh - 5 Column View</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0b0e14; color: #fff; margin: 0; padding: 20px; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 10px; }
        .lag-box { background: #1a1f29; padding: 10px 20px; border-radius: 8px; border-left: 4px solid #ff3e3e; }
        
        .dashboard-grid { 
            display: grid; 
            grid-template-columns: 1fr 1fr 1fr 1fr 1.5fr; 
            gap: 15px; 
            margin-top: 20px; 
            height: 80vh;
        }
        
        .column { background: #161b22; border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; border: 1px solid #30363d; }
        .col-header { background: #21262d; padding: 12px; font-weight: bold; text-transform: uppercase; font-size: 0.85em; letter-spacing: 1px; }
        .feed { padding: 15px; overflow-y: auto; flex-grow: 1; font-family: 'Consolas', monospace; font-size: 0.9em; }
        
        .card { background: #0d1117; border: 1px solid #30363d; padding: 12px; margin-bottom: 12px; border-radius: 6px; animation: fadeIn 0.3s ease-out; position: relative; }
        .log-card { border-left: 3px solid #58a6ff; font-size: 0.8em; }
        .success-card { border-left: 4px solid #2ea44f; background: #1b2a1e; }
        .failure-card { border-left: 4px solid #cf222e; background: #2a1b1b; }
        .task-id { color: #58a6ff; font-size: 0.75em; margin-bottom: 5px; }
        pre { white-space: pre-wrap; word-wrap: break-word; margin: 0; color: #d1d5da; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 Elite AI Agent Mesh <small style="color:#888; font-size:0.5em;">v4.3 (Algo Solver Ops)</small></h1>
        <div class="lag-box">SYSTEM LAG: <span id="lag-val">0</span></div>
    </div>

    <div class="dashboard-grid">
        <div class="column"><div class="col-header">🚀 Tasks</div><div class="feed" id="col-tasks"></div></div>
        <div class="column"><div class="col-header">⚙️ Code</div><div class="feed" id="col-solutions"></div></div>
        <div class="column"><div class="col-header">🧪 Sandbox</div><div class="feed" id="col-verified"></div></div>
        <div class="column"><div class="col-header">🕵️ Reviews</div><div class="feed" id="col-reviews"></div></div>
        <div class="column"><div class="col-header">📜 Unified Logs</div><div class="feed" id="col-logs"></div></div>
    </div>

    <script>
        const eventSource = new EventSource("/stream");
        const lagVal = document.getElementById("lag-val");

        eventSource.onmessage = function(e) {
            const data = JSON.parse(e.data);
            if (data.lag !== undefined) lagVal.innerText = data.lag;

            if (data.type === 'task') addCard('col-tasks', data.content);
            if (data.type === 'solution') addCard('col-solutions', data.content);
            if (data.type === 'verified') {
                const statusClass = data.success ? 'success-card' : 'failure-card';
                addExtraCard('col-verified', data.content, statusClass);
            }
            if (data.type === 'review') addCard('col-reviews', data.content);
            if (data.type === 'log') addCard('col-logs', `[${data.agent}] ${data.content}`, 'log-card');
        };

        function addCard(colId, text, className = "") {
            const container = document.getElementById(colId);
            const card = document.createElement("div");
            card.className = "card " + className;
            card.innerHTML = `<div class="task-id">${new Date().toLocaleTimeString()}</div><pre>${text}</pre>`;
            container.prepend(card);
            if (container.children.length > 50) container.removeChild(container.lastChild);
        }

        function addExtraCard(colId, text, className = "") {
            const container = document.getElementById(colId);
            const card = document.createElement("div");
            card.className = "card " + className;
            card.innerHTML = `<div class="task-id">${new Date().toLocaleTimeString()}</div><pre>${text}</pre>`;
            container.prepend(card);
            if (container.children.length > 50) container.removeChild(container.lastChild);
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
        consumer.subscribe(['ai_topic', 'ai_solutions', 'ai_reviews', 'ai_verified_solutions', 'ai_telemetry'])
        tp = TopicPartition('ai_topic', 0)

        while True:
            msg_pack = consumer.poll(timeout_ms=500)
            
            # Calculate Lag
            try:
                end_offsets = consumer.end_offsets([tp])
                grp_offsets = admin.list_consumer_group_offsets('consumer-group') 
                lag = end_offsets[tp] - (grp_offsets[tp].offset if tp in grp_offsets else 0)
            except: lag = 0

            yield f"data: {json.dumps({'lag': lag})}\n\n"

            for tp_key, messages in msg_pack.items():
                for msg in messages:
                    msg_type = 'unknown'
                    content = ''
                    agent = 'system'
                    success = True
                    
                    if msg.topic == 'ai_topic':
                        msg_type = 'task'
                        content = msg.value.get('task', '')
                    elif msg.topic == 'ai_solutions':
                        msg_type = 'solution'
                        content = msg.value.get('solution', '')
                    elif msg.topic == 'ai_reviews':
                        msg_type = 'review'
                        content = msg.value.get('review', '')
                    elif msg.topic == 'ai_verified_solutions':
                        msg_type = 'verified'
                        success = msg.value.get('success', True)
                        status = "PASS" if success else "FAIL"
                        content = f"STATUS: {status}\nOUT: {msg.value.get('exec_output', '')[:200]}"
                    elif msg.topic == 'ai_telemetry':
                        if msg.value.get('type') == 'log':
                            msg_type = 'log'
                            content = msg.value.get('message', '')
                            agent = msg.value.get('agent', 'unknown')
                        else:
                            continue # Skip metrics for now

                    if msg_type != 'unknown':
                        yield f"data: {json.dumps({'type': msg_type, 'content': content, 'agent': agent, 'success': success})}\n\n"

    return Response(monitor(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)