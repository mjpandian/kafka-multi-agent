import os, json, time
from kafka import KafkaConsumer, KafkaProducer
from openai import OpenAI

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
OLLAMA_URL = os.getenv("OLLAMA_URL")

# --- KAFKA CONNECTION HELPERS ---

def connect_consumer():
    while True:
        try:
            print(f"📡 Connecting Consumer to {KAFKA_BROKER}...", flush=True)
            return KafkaConsumer(
                'ai_topic',
                bootstrap_servers=KAFKA_BROKER,
                api_version=(3, 5, 0),
                group_id='agent-b-group',
                auto_offset_reset='earliest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                request_timeout_ms=30000
            )
        except Exception as e:
            print(f"⌛ Consumer waiting for Kafka... ({e})", flush=True)
            time.sleep(5)

def connect_producer():
    while True:
        try:
            print(f"📡 Connecting Producer to {KAFKA_BROKER}...", flush=True)
            return KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                api_version=(3, 5, 0),
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
        except Exception as e:
            print(f"⌛ Producer waiting for Kafka... ({e})", flush=True)
            time.sleep(5)

# --- INITIALIZATION ---

client = OpenAI(base_url=OLLAMA_URL, api_key="ollama")

if __name__ == "__main__":
    consumer = connect_consumer()
    producer = connect_producer()
    print("👂 Agent B (Consumer) is officially listening...", flush=True)
    
    for message in consumer:
        task = message.value.get('task', 'No task found')
        print(f"📥 Received Task: {task}", flush=True)
        
        try:
            # 1. Get Solution from Ollama
            resp = client.chat.completions.create(
                model="gemma3:1b",
                messages=[{"role": "user", "content": f"Solve this coding task: {task}"}]
            )
            
            solution_content = resp.choices[0].message.content
            print(f"✅ Solution Generated", flush=True)

            # 2. Publish to 'ai_solutions' for the Reviewer
            producer.send('ai_solutions', {
                'task': task,
                'solution': solution_content
            })
            producer.flush() # Ensure it's sent before next iteration
            print(f"📤 Sent to ai_solutions topic", flush=True)

        except Exception as e:
            print(f"❌ Error processing task: {e}", flush=True)