# 🧠 AI-Mesh: Kafka-Driven Multi-Agent System
An event-driven, self-healing AI ecosystem where specialized agents collaborate via Apache Kafka to generate, solve, and critique coding tasks, now featuring the **AI Consensus Arena**.

## 🚀 Key Features
- **5-Agent Mesh:** Producer -> Consumer -> Sandbox -> Reviewer -> Persistence.
- **Consensus Arena:** A multi-agent feedback loop (Coordinator -> Solvers -> Judge) for iterative refinement of complex tasks.
- **Self-Healing:** Retries connections until Kafka/Ollama/Qdrant are ready.
- **Adaptive Throttling (The Governor):** Prevents system saturation by monitoring consumer lag.
- **Episodic Memory:** Uses Qdrant for storing and retrieving successful patterns and "Gold Standard" solutions.
- **Live Observability:** Real-time telemetry dashboard with SSE (Server-Sent Events) for unified monitoring.

## 🔄 The Consensus Arena Workflow
1. **Coordinator:** Dispatches a task, injecting similar "Gold Standard" solutions from Qdrant as few-shot context.
2. **Solvers (Alpha, Beta, Gamma):** Propose solutions, performing an internal "Self-Reflexion" pass before submission.
3. **Judge:** Evaluates proposals against a structured rubric (Accuracy, Tone, Reasoning) and provide feedback for refinement.
4. **Iterative Refinement:** Solvers update their work based on Judge feedback until consensus is reached or a round limit is hit.

## 🐳 Deployment (Cross-Platform)

### 1. Standard (Linux/Windows)
```bash
docker compose up -d --build
```

### 2. Apple Silicon (Mac M3)
Uses optimized arm64 images and resource limits.
```bash
docker compose -f docker-compose.mac-m3.yaml up -d --build
```

## 📜 Topics & Telemetry
- **`arena_tasks`**: Initial task broadcasts.
- **`arena_proposals`**: Solver submissions to the Judge.
- **`arena_feedback`**: Judge's critiques back to Solvers.
- **`ai_telemetry`**: Unified stream for the real-time Dashboard.

---
*Verified by Antigravity - Optimized for M3 & Agentic Consensus*

---