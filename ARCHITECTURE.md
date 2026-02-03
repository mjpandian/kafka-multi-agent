# 🏗️ AI-Mesh: Architecture & Design

This document details the architecture of the AI-Mesh system, focusing on the integration of **Qdrant-based Memory** and **Event-Driven Telemetry**.

## 🛰️ System Overview

The system transitions from a simple pipeline to a **Closed-Loop Learning Ecosystem**.

![AI-Mesh Architecture Diagram](file:///C:/Users/mjpan/.gemini/antigravity/brain/27ed6ca3-cc5e-4f03-8145-bf6d951cb71f/ai_mesh_architecture_diagram.png)

### 🗺️ Data Flow Map

- **[Producer]** --(task)--> **[Kafka: ai_topic]** --(task)--> **[Consumer]**
- **[Consumer]** --(code)--> **[Kafka: ai_solutions]** --(code)--> **[Sandbox]** & **[Reviewer]**
- **[Sandbox]** --(result)--> **[Kafka: ai_verified_solutions]** --(result)--> **[Dashboard]**
- **[Reviewer]** --(critique)--> **[Kafka: ai_reviews]** --(critique)--> **[Dashboard]** & **[Persistence]**
- **[All Agents]** --(telemetry/logs)--> **[Kafka: ai_telemetry]** --(logs)--> **[Dashboard]**
- **[Memory (Qdrant)]** <--> (Experience Store) <--> **[Sandbox/Agents]**
- **[Persistence]** --(Archive)--> **[CSV Storage]**

## 🧠 Key Components

### 1. Qdrant-Based Memory (`MemorySkill`)
- **Purpose**: To provide persistent "experience" to the agents via vector search.
- **Data Points**:
    - **Sandbox**: Stores failure logs and error patterns. If code fails, the error is vectorized and stored.
    - **Producer/Consumer**: Can query memory to avoid repeating mistakes or to find similar successful patterns (extensibility).
    - **Implementation**: Uses `ollama` for embeddings (`nomic-embed-text`) and `Qdrant` for storage and retrieval.

### 2. Self-Healing Loop
- **Error Correction**: When the `Sandbox` detects a failure, it re-publishes the task to `ai_topic` with the error message prefixed as "FIX THIS CODE:".
- **Reinforcement**: The `Reviewer` provides a final critique that is archived by the `Persistence` agent, creating a historical dataset of tasks, solutions, and reviews.

### 3. Structured Telemetry
- **Topic**: `ai_telemetry`
- **Schema**:
    ```json
    {
      "agent": "consumer",
      "type": "log|metric|event",
      "message": "...",
      "value": 0.85,
      "timestamp": 123456789.0,
      "extra": {}
    }
    ```

## 🔄 Interaction Flow

1.  **Producer** brainstorms a task and publishes to `ai_topic`.
2.  **Consumer** translates the task into Python code and publishes to `ai_solutions`.
3.  **Sandbox** executes the code. 
    - On **Success**: Publishes results to `ai_verified_solutions`.
    - On **Failure**: Stores error in **Qdrant** and requests a fix via `ai_topic`.
4.  **Reviewer** critiques the solution and publishes to `ai_reviews`.
5.  **Persistence** agent captures reviews and saves the full cycle to CSV.
6.  **Dashboard** listens to all topics and unified `ai_telemetry` for real-time visualization.
