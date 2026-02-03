# 🧠 AI-Mesh: Kafka-Driven Multi-Agent System
An event-driven, self-healing AI ecosystem where specialized agents collaborate via Apache Kafka to generate, solve, and critique coding tasks.

## 🚀 Key Features
- **5-Agent Chain:** Producer -> Consumer -> Sandbox -> Reviewer -> Persistence.
- **Self-Healing:** Retries connections until Kafka/Ollama/Qdrant are ready.
- **Adaptive Throttling (The Governor):** The Producer monitors Consumer Lag. If the backlog exceeds 3 tasks, the Producer automatically pauses to prevent system saturation.
- **Dynamic Memory:** Agents use Qdrant to store and retrieve "memories" (failures, successes, and patterns) to improve over time.
- **Live Observability:** 5-column dashboard with real-time lag metrics, status indicators, and unified agent logs.


## 📈 Monitoring the "Governor"
Open the **Dashboard** (`localhost:5000`).
1. Watch the **Lag Meter** (Top Right).
2. When Lag hits **3**, you will see the **Producer** throttle.
3. Once the **Consumer** processes the backlog and Lag drops, the Producer will resume.

## 🛠️ Architecture: The Feedback Loop
The system uses a "Closed Loop" control pattern. By querying the `KafkaAdminClient`, the Producer stays aware of the Consumer's health, preventing the common "Message Flooding" issue in AI pipelines.

## 🔄 The Agent Workflow
1.  **Producer:** Brainstorms a coding task (Gemma 3), checking memory to avoid repetition.
2.  **Consumer:** Writes the Python code for the task, leveraging best practices from memory.
3.  **Sandbox:** Executes the code in an isolated environment. If it fails, it logs the error to memory and requests a fix.
4.  **Reviewer:** Performs a "Senior Dev" critique of the code and execution results.
5.  **Persistence:** Saves the full task/solution/review trio to `./data/ai_history.csv` for long-term storage.
6.  **Dashboard:** Streams the entire conversation, metrics, and logs live to the web.
 

## 🛠️ Components & Topics
- **Topic `ai_topic`**: Tasks from Producer/Sandbox -> Consumer.
- **Topic `ai_solutions`**: Code from Consumer -> Sandbox/Reviewer.
- **Topic `ai_verified_solutions`**: Execution results from Sandbox -> Dashboard/Reviewer.
- **Topic `ai_reviews`**: Critiques from Reviewer -> Dashboard/Persistence.
- **Topic `ai_telemetry`**: Unified logs and metrics from all agents -> Dashboard.

## 🖥️ The Dashboard (Visualizing the Mesh)
The system features a **Five-Column Real-Time Interface** for maximum observability:

- **Column 1 (Tasks):** Original problem descriptions.
- **Column 2 (Code):** Generated Python implementations.
- **Column 3 (Sandbox):** Real-time execution status (PASS/FAIL) and output.
- **Column 4 (Reviews):** Senior-level critique and optimization tips.
- **Column 5 (Logs):** Unified stream of internal agent telemetry and "thinking" logs.


### Key Metrics
- **System Lag:** Located in the top right, this shows the pressure on the Consumer. A lag > 3 triggers the Governor.

## 🚀 Deployment
### 1. Prerequisites
Docker & Docker Compose installed.

Ollama running locally with gemma3:1b installed.

Ensure Ollama is listening on http://host.docker.internal:11434.

### 2. Launch
```bash
docker compose up --build
### # Start the entire mesh in the background
docker compose up --build -d

# Scale the consumers to handle high volume
docker compose up -d --scale consumer-agent=3

# View live logs for all agents
docker compose logs -f

## 🧪 System Stress Testing
To verify the **Adaptive Throttling** (Governor) logic:
1. Run the provided `stress_test.py` script.
2. This will inject 50 messages into the `ai_topic` instantly.
3. Observe the Dashboard:
    - **Lag Meter** climbs above 10.
    - **Status Light** changes to **YELLOW/THROTTLED**.
    - **Producer Agent** logs will show: `🛑 LAG TOO HIGH. Throttling...`
4. Once the Consumers clear the backlog, the system will automatically return to **GREEN/ACTIVE**.

 
## 🐳 Docker Operations Cheat Sheet

Use these commands to manage the AI-Mesh ecosystem from the root directory.

### 🚀 Lifecycle Management
- **Start Mesh (Standard)**: `docker-compose up --build`
- **Start Mesh (Detached)**: `docker-compose up --build -d`
- **Stop Mesh**: `docker-compose stop`
- **Shut Down & Clean (Recommended)**: `docker-compose down`
- **Wipe All (Images/Volumes)**: `docker-compose down --rmi all --volumes`

### 📈 Scaling & Management
- **Scale Consumers**: `docker-compose up -d --scale consumer-agent=3`
- **Check Process Status**: `docker-compose ps`
- **Rebuild Single Agent**: `docker-compose build producer-agent && docker-compose up -d producer-agent`

### 📜 Observability & Logs
- **Follow All Logs**: `docker-compose logs -f`
- **Follow Specific Agent**: `docker-compose logs -f sandbox-agent`
- **Check Dashboard**: Open `http://localhost:5000` in your browser.
- **Check Kafka UI**: Open `http://localhost:8080` in your browser.

---