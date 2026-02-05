import os, json, time
from flask import Flask, Response, render_template_string
from kafka import KafkaConsumer, TopicPartition, KafkaAdminClient
from utils.telemetry_utils import TelemetryLogger

app = Flask(__name__)
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
telemetry = TelemetryLogger("dashboard")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Agent Mesh - Arena Edition</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0b0e14; color: #fff; margin: 0; padding: 20px; overflow-x: hidden; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 15px; }
        .status-badge { font-size: 0.6em; padding: 4px 10px; border-radius: 20px; background: #2ea44f; margin-left: 10px; }
        .lag-box { background: #1a1f29; padding: 10px 20px; border-radius: 8px; border-left: 4px solid #ff3e3e; font-weight: bold; }
        
        .dashboard-grid { 
            display: grid; 
            grid-template-columns: 1fr 2fr 1.5fr 1.2fr; 
            gap: 15px; 
            margin-top: 20px; 
            height: calc(100vh - 120px);
        }
        
        .column { background: #161b22; border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; border: 1px solid #30363d; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
        .col-header { background: #21262d; padding: 12px; font-weight: bold; text-transform: uppercase; font-size: 0.8em; letter-spacing: 1.5px; border-bottom: 1px solid #30363d; color: #8b949e; }
        .feed { padding: 15px; overflow-y: auto; flex-grow: 1; font-family: 'Fira Code', 'Consolas', monospace; font-size: 0.85em; scroll-behavior: smooth; }
        
        .card { background: #0d1117; border: 1px solid #30363d; padding: 12px; margin-bottom: 12px; border-radius: 6px; animation: slideIn 0.3s ease-out; position: relative; }
        .log-card { border-left: 3px solid #58a6ff; font-size: 0.75em; opacity: 0.8; }
        .proposal-card { border-left: 4px solid #f2cf66; background: #1c1a14; }
        .feedback-card { border-left: 4px solid #ff7b72; background: #1c1414; }
        .task-card { border-left: 4px solid #a371f7; background: #17141c; }
        
        .task-id { color: #58a6ff; font-size: 0.7em; margin-bottom: 8px; font-weight: bold; opacity: 0.7; }
        .persona-tag { font-size: 0.7em; background: #30363d; color: #c9d1d9; padding: 2px 8px; border-radius: 12px; margin-left: 8px; border: 1px solid #444; }
        pre { white-space: pre-wrap; word-wrap: break-word; margin: 0; color: #d1d5da; line-height: 1.4; }
        
        @keyframes slideIn { from { opacity: 0; transform: translateX(-20px); } to { opacity: 1; transform: translateX(0); } }
        
        /* Custom Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0b0e14; }
        ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: #444; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏟️ AI CONSENSUS ARENA <span class="status-badge" id="status-indicator">CONNECTED</span></h1>
        <div class="lag-box">SYSTEM LAG: <span id="lag-val">0</span></div>
    </div>

    <div class="dashboard-grid">
        <div class="column"><div class="col-header">🚀 Arena Tasks</div><div class="feed" id="col-arena-tasks"></div></div>
        <div class="column"><div class="col-header">⚔️ Expert Proposals</div><div class="feed" id="col-arena-proposals"></div></div>
        <div class="column"><div class="col-header">⚖️ Judge Feedback</div><div class="feed" id="col-arena-feedback"></div></div>
        <div class="column"><div class="col-header">📜 Unified Logs</div><div class="feed" id="col-logs"></div></div>
    </div>

    <script>
        const eventSource = new EventSource("/stream");
        const lagVal = document.getElementById("lag-val");
        const status = document.getElementById("status-indicator");

        console.log("🚀 Dashboard JS initialized. Connecting to stream...");

        eventSource.onopen = () => {
            console.log("✅ Stream Connected");
            status.innerText = "CONNECTED";
            status.style.background = "#2ea44f";
        };

        eventSource.onerror = (e) => {
            console.error("❌ Stream Connection Error:", e);
            status.innerText = "RECONNECTING...";
            status.style.background = "#d29922";
        };

        eventSource.onmessage = function(e) {
            try {
                const data = JSON.parse(e.data);
                console.log("📥 Received:", data.type, data);
                
                if (data.lag !== undefined) lagVal.innerText = data.lag;

                if (data.type === 'arena-task') {
                    const domain = (data.domain || 'general').toUpperCase();
                    addCard('col-arena-tasks', "[" + domain + "]\\n" + data.content, 'task-card');
                }
                if (data.type === 'proposal') {
                    const round = data.round || 1;
                    const solver = data.solver_id || 'unknown';
                    const persona = data.persona || 'Expert';
                    const header = "ROUND " + round + " | " + solver + " <span class='persona-tag'>" + persona + "</span>";
                    addCard('col-arena-proposals', data.content, 'proposal-card', header);
                }
                if (data.type === 'feedback') {
                    const round = data.round || 1;
                    const stat = (data.status || 'refine').toUpperCase();
                    const header = "ROUND " + round + " | " + stat;
                    addCard('col-arena-feedback', data.content, 'feedback-card', header);
                }
                if (data.type === 'log') {
                    addCard('col-logs', "[" + (data.agent || 'system') + "] " + (data.content || ''), 'log-card');
                }
            } catch (err) {
                console.error("❌ Dashboard Parse Error:", err);
            }
        };

        function addCard(colId, text, className = "", header = "") {
            const container = document.getElementById(colId);
            if (!container) {
                console.warn("⚠️ Column not found:", colId);
                return;
            }
            const card = document.createElement("div");
            card.className = "card " + className;
            const timeStr = new Date().toLocaleTimeString();
            card.innerHTML = "<div class='task-id'>" + timeStr + " " + header + "</div><pre>" + text + "</pre>";
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
        telemetry.log("🔌 New dashboard client connected. Initializing Kafka...")
        
        # Use a fresh group ID every time
        group_id = f"dashboard-client-{int(time.time())}"
        
        try:
            consumer = KafkaConsumer(
                bootstrap_servers=KAFKA_BROKER,
                api_version=(3, 5, 0),
                group_id=group_id,
                auto_offset_reset='earliest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            consumer.subscribe(['arena_tasks', 'arena_proposals', 'arena_feedback', 'ai_telemetry'])
            
            # 1. Immediate Welcome Message to verify the pipe is open
            welcome_msg = {
                'type': 'log', 
                'content': '✅ Stream established. Retrieving arena history...', 
                'agent': 'dashboard'
            }
            yield f"data: {json.dumps(welcome_msg)}\n\n"
            
            # 2. Main loop
            while True:
                msg_pack = consumer.poll(timeout_ms=500)
                
                # Send a heartbeat
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"

                for tp_key, messages in msg_pack.items():
                    for msg in messages:
                        msg_type = 'unknown'
                        content = ''
                        agent = 'system'
                        extra = {}
                        
                        if msg.topic == 'arena_tasks':
                            msg_type = 'arena-task'
                            content = msg.value.get('prompt', '')
                            extra = {'domain': msg.value.get('domain', 'general')}
                        elif msg.topic == 'arena_proposals':
                            msg_type = 'proposal'
                            content = msg.value.get('content', '')
                            extra = {
                                'solver_id': msg.value.get('solver_id', ''),
                                'persona': msg.value.get('persona', ''),
                                'round': msg.value.get('round', 1)
                            }
                        elif msg.topic == 'arena_feedback':
                            msg_type = 'feedback'
                            content = msg.value.get('feedback', '')
                            extra = {
                                'round': msg.value.get('round', 1),
                                'status': msg.value.get('status', 'refine')
                            }
                        elif msg.topic == 'ai_telemetry':
                            if msg.value.get('type') == 'log':
                                msg_type = 'log'
                                content = msg.value.get('message', '')
                                agent = msg.value.get('agent', 'unknown')
                            else:
                                continue 

                        if msg_type != 'unknown':
                            data = {'type': msg_type, 'content': content, 'agent': agent}
                            data.update(extra)
                            # Log to terminal for debugging
                            if msg_type != 'log':
                                print(f"� Forwarding: {msg_type} for {agent}", flush=True)
                            yield f"data: {json.dumps(data)}\n\n"

        except Exception as e:
            telemetry.log(f"❌ Dashboard stream error: {e}")
            yield f"data: {json.dumps({'type': 'log', 'content': f'ERROR: {str(e)}', 'agent': 'system'})}\n\n"

    return Response(monitor(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
