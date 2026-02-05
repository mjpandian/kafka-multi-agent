import os, json, time, uuid
from kafka import KafkaConsumer, KafkaProducer
from utils.telemetry_utils import TelemetryLogger
from qdrant_client import QdrantClient

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
telemetry = TelemetryLogger("coordinator")
qdrant_mem = None
try:
    qdrant_mem = QdrantClient(host=QDRANT_HOST, port=6333)
    telemetry.log(f"✅ Qdrant Client linked to {QDRANT_HOST}")
except Exception as e:
    telemetry.log(f"❌ Qdrant Link Failed: {e}")
MODEL_NAME = os.getenv("ARENA_COORDINATOR_MODEL", "gemma3:1b")

def connect_kafka():
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                api_version=(3, 5, 0),
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            consumer = KafkaConsumer(
                'arena_feedback',
                bootstrap_servers=KAFKA_BROKER,
                api_version=(3, 5, 0),
                group_id='coordinator-group',
                auto_offset_reset='earliest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            return producer, consumer
        except Exception as e:
            telemetry.log(f"⌛ Coordinator waiting for Kafka... ({e})")
            time.sleep(5)

if __name__ == "__main__":
    producer, consumer = connect_kafka()
    telemetry.log("🏟️ Arena Coordinator (Synchronous Mode) is active.")

    # Domains to cycle through
    DOMAINS = [
        {"domain": "sports", "prompt": "Predict the outcome: Lakers vs Celtics. Consider current momentum and player standings."},
        {"domain": "medical", "prompt": "Patient shows signs of persistent cough and night sweats. Biopsy pending. What are the top 3 differential diagnoses?"},
        {"domain": "career", "prompt": "Optimize this LinkedIn Summary for a Senior DevOps Engineer: 'Expert in AWS and Kubernetes looking for new roles.'"},
        {"domain": "coding", "prompt": "Write a highly optimized Python function to find the longest palindromic substring."}
    ]

    while True:
        for task_info in DOMAINS:
            task_id = str(uuid.uuid4())
            telemetry.log(f"🌟 Starting New Arena: [{task_info['domain'].upper()}] - {task_id}")
            
            # Agentic Memory Retrieval
            telemetry.log(f"🔎 Querying Qdrant for past experience...")
            memory_results = []
            try:
                if qdrant_mem:
                    # Use a more robust search
                    try:
                        hits = qdrant_mem.search(
                            collection_name="arena_memory",
                            query_vector=[0.5],
                            limit=2
                        )
                    except AttributeError:
                        # Fallback for different client versions
                        hits = qdrant_mem.query_points(
                            collection_name="arena_memory",
                            query=[0.5],
                            limit=2
                        ).points
                    memory_results = [h.payload.get('solution', '') for h in hits]
            except Exception as e:
                telemetry.log(f"⚠️ Memory retrieval failed: {e}")

            context_str = "\n\n".join([f"PAST SUCCESSFUL SOLUTION:\n{m}" for m in memory_results])
            final_prompt = task_info['prompt']
            if memory_results:
                final_prompt = f"Use the following past successful solutions as reference to improve your response:\n{context_str}\n\nCURRENT TASK:\n{task_info['prompt']}"

            # Publish task
            producer.send('arena_tasks', {
                'task_id': task_id,
                'domain': task_info['domain'],
                'prompt': final_prompt
            })
            producer.flush()
            
            # Synchronous Wait: Wait for judgment to reach 'complete'
            telemetry.log(f"⏳ Waiting for {task_id} to finish refinement rounds...")
            finished = False
            while not finished:
                messages = consumer.poll(timeout_ms=1000)
                for tp, msgs in messages.items():
                    for msg in msgs:
                        if msg.value.get('task_id') == task_id and msg.value.get('status') == 'complete':
                            telemetry.log(f"✅ Task {task_id} COMPLETED after refinement.")
                            finished = True
                            break
                    if finished: break
            
            telemetry.log(f"🏁 Arena session finished. Resting for 10s...")
            time.sleep(10)
