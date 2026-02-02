# 🏗️ AI-Mesh: Architecture & Design

This document details the enhanced architecture of the AI-Mesh system, focusing on the integration of **Persistent Memory** (`mem0`) and **Self-Learning Loops** (`agent-lightning`).

## 🛰️ System Overview

The system transitions from a simple pipeline to a **Closed-Loop Learning Ecosystem**.

![AI-Mesh Architecture Diagram](file:///C:/Users/mjpan/.gemini/antigravity/brain/27ed6ca3-cc5e-4f03-8145-bf6d951cb71f/ai_mesh_architecture_diagram.png)

### 🗺️ Data Flow Map

- **[Producer]** --(task)--> **[Kafka: ai_topic]** --(task)--> **[Consumer]**
- **[Consumer]** --(code)--> **[Kafka: ai_solutions]** --(code)--> **[Sandbox]**
- **[Sandbox]** --(result)--> **[Kafka: ai_verified_solutions]** --(result)--> **[Reviewer]**
- **[Reviewer]** --(reward/critique)--> **[Kafka: ai_reviews]**
- **[Supervisor]** --(Audit/Report)--> **[Telemetry]**
- **[Memory (mem0)]** <--> (Knowledge Sync) <--> **[All Agents]**
- **[Learning Optimizer]** --(Self-Correction)--> **[Prompts/Skills]**
- **[Telemetry]** --(Metrics)--> **[Dashboard]**

## 🧠 Key Components

### 1. Persistent Memory (`mem0`)
- **Purpose**: To provide long-term "experience" to the agents.
- **Data Points**:
    - **Producer**: Stores task categories to ensure diversity and progressively increasing difficulty.
    - **Consumer**: Stores "Best Practices" and "Fix Recipes". If a piece of code is fixed in the Sandbox, the correction is stored as a memory.
    - **Retrieval**: Agents query memory during their reasoning phase to contextualize the current task.

### 2. Self-Learning Loop (`agent-lightning`)
- **Reward Signal**: The `Reviewer` generates a performance score (0-1) based on:
    - Code correctness (from Sandbox).
    - Efficiency and readability.
    - Adherence to requirements.
- **Optimization**: `agent-lightning` uses these scores to perform **Prompt Optimization**. It refines the system instructions of the Producer and Consumer to maximize reward over time.

### 3. Structured Telemetry
- **Topic**: `ai_telemetry`
- **Schema**:
    ```json
    {
      "agent": "consumer",
      "timestamp": "ISO-8601",
      "latency_ms": 1200,
      "tokens_used": 450,
      "reward_score": 0.85,
      "memory_hits": 2
    }
    ```

## 🔄 Interaction Flow

1.  **Producer** brainstorms a task, checking **Memory** to avoid repetition.
2.  **Consumer** receives the task, pulls related snippets from **Memory**, and generates code.
3.  **Sandbox** executes the code. If it fails, feedback is sent to **Consumer** AND stored in **Memory**.
4.  **Reviewer** critiques the final code and assigns a **Reward Score**.
5.  **Learning Optimizer** aggregates scores and periodically updates the **Agent Skills**.
6.  **Telemetry** captures the entire lifecycle for real-time visualization on the **Dashboard**.
