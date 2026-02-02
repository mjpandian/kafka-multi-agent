import os, json, time
from kafka import KafkaProducer, KafkaConsumer, TopicPartition, KafkaAdminClient
from openai import OpenAI
from utils.telemetry_utils import TelemetryLogger

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TOPIC = "ai_topic"
GROUP_ID = "consumer-group" # Updated to match dashboard group

def get_current_lag(producer_instance):
    try:
        tp = TopicPartition(TOPIC, 0)
        
        # Use a temporary consumer for offset lookups
        temp_consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BROKER,
            api_version=(3, 5, 0)
        )
        end_offsets = temp_consumer.end_offsets([tp])
        latest_offset = end_offsets[tp]
        temp_consumer.close()

        # Check the group's progress
        admin = KafkaAdminClient(bootstrap_servers=KAFKA_BROKER, api_version=(3, 5, 0))
        offsets = admin.list_consumer_group_offsets(GROUP_ID)
        admin.close()
        
        if tp in offsets:
            current_consumer_offset = offsets[tp].offset
            return latest_offset - current_consumer_offset
        return 0
    except Exception as e:
        print(f"⚠️ Could not calculate lag: {e}")
        return 0

# Initialize
telemetry = TelemetryLogger("producer")
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    api_version=(3, 5, 0),
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)
client = OpenAI(base_url=os.getenv("OLLAMA_URL"), api_key="ollama")

if __name__ == "__main__":
    telemetry.log("🚀 Adaptive Producer is active.")
    while True:
        # 1. CHECK THE BRAKES (Lag check)
        lag = get_current_lag(producer)
        
        if lag >= 3:
            telemetry.log(f"🛑 LAG THRESHOLD MET ({lag}). Waiting for cycles to complete...")
            time.sleep(5)
            continue
        
        # 2. PRODUCE TASK (The Algorithm Judge)
        try:
            resp = client.chat.completions.create(
                model="gemma3:1b",
                messages=[{"role": "user", "content": "Suggest a LeetCode EASY/MEDIUM algorithm problem description. Include 2 simple test cases (input/expected). Focus on data structures (linked list, tree, array). Keep it concise."}]
            )
            task = resp.choices[0].message.content
            producer.send(TOPIC, {'task': task})
            telemetry.log(f"⚖️ Judge Published Challenge: {task[:40]}...")
        except Exception as e:
            telemetry.log(f"❌ Producer Error: {e}")

        # Base delay between tasks
        time.sleep(10)