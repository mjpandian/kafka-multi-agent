import os, json, time
from kafka import KafkaConsumer, KafkaProducer
from openai import OpenAI

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
OLLAMA_URL = os.getenv("OLLAMA_URL")

from utils.telemetry_utils import TelemetryLogger
telemetry = TelemetryLogger("consumer")

# --- KAFKA CONNECTION HELPERS ---

def connect_consumer():
    while True:
        try:
            telemetry.log(f"📡 Connecting Consumer to {KAFKA_BROKER}...")
            return KafkaConsumer(
                'ai_topic',
                bootstrap_servers=KAFKA_BROKER,
                api_version=(3, 5, 0),
                group_id='consumer-group',
                auto_offset_reset='earliest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
        except Exception as e:
            telemetry.log(f"⌛ Consumer waiting for Kafka... ({e})")
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
    telemetry.log("👂 Consumer Agent is active.")
    
    for message in consumer:
        task = message.value.get('task', 'No task found')
        telemetry.log(f"📥 Received Task: {task[:30]}...")
        
        try:
            # 1. Get Solution from Ollama (The Optimized Coder)
            resp = client.chat.completions.create(
                model="gemma3:1b",
                messages=[{"role": "user", "content": f"You are a Senior Software Engineer. Solve this LeetCode problem with an optimized Python implementation. Analyze the constraints and use efficient data structures. ONLY output the code block and a short complexity analysis: {task}"}]
            )
            
            solution_content = resp.choices[0].message.content
            telemetry.log(f"✅ Solution Generated")

            # 2. Publish to 'ai_solutions' for the Reviewer
            producer.send('ai_solutions', {
                'task': task,
                'solution': solution_content
            })
            producer.flush() # Ensure it's sent before next iteration
            telemetry.log(f"📤 Sent to ai_solutions topic")

        except Exception as e:
            telemetry.log(f"❌ Error processing task: {e}")