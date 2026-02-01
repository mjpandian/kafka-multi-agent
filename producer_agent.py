import os, json, time
from kafka import KafkaProducer, KafkaConsumer, TopicPartition
from openai import OpenAI

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TOPIC = "ai_topic"
GROUP_ID = "agent-b-group" # The group we are monitoring

def get_current_lag(producer_client):
    try:
        tp = TopicPartition(TOPIC, 0)
        # Get latest offset produced
        end_offsets = producer_client.end_offsets([tp])
        latest_offset = end_offsets[tp]

        # Use a temporary consumer to check the group's progress
        from kafka import KafkaAdminClient
        admin = KafkaAdminClient(bootstrap_servers=KAFKA_BROKER, api_version=(3, 5, 0))
        offsets = admin.list_consumer_group_offsets(GROUP_ID)
        
        if tp in offsets:
            current_consumer_offset = offsets[tp].offset
            return latest_offset - current_consumer_offset
        return 0
    except Exception as e:
        print(f"⚠️ Could not calculate lag: {e}")
        return 0

# Initialize
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    api_version=(3, 5, 0),
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)
client = OpenAI(base_url=os.getenv("OLLAMA_URL"), api_key="ollama")

if __name__ == "__main__":
    print("🚀 Adaptive Producer is active.")
    while True:
        # 1. CHECK THE BRAKES (Lag check)
        lag = get_current_lag(producer)
        
        if lag > 10:
            print(f"🛑 LAG TOO HIGH ({lag}). Throttling production for 30s...", flush=True)
            time.sleep(30)
            continue
        
        # 2. PRODUCE TASK
        try:
            resp = client.chat.completions.create(
                model="gemma3:1b",
                messages=[{"role": "user", "content": "Suggest a Python task in 5 words."}]
            )
            task = resp.choices[0].message.content
            producer.send(TOPIC, {'task': task})
            print(f"📤 Published Task. Current Lag: {lag}", flush=True)
        except Exception as e:
            print(f"❌ Producer Error: {e}")

        # Base delay between tasks
        time.sleep(10)