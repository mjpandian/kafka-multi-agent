import os, json, csv, time
from kafka import KafkaConsumer

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
CSV_FILE = "/app/data/ai_history.csv"

def initialize_persistence():
    while True:
        try:
            return KafkaConsumer(
                'ai_reviews',
                bootstrap_servers=KAFKA_BROKER,
                api_version=(3, 5, 0),
                group_id='persistence-group',
                auto_offset_reset='earliest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
        except Exception as e:
            print(f"⌛ Persistence waiting for Kafka... {e}", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    consumer = initialize_persistence()
    print("💾 Persistence Agent active. Archiving to CSV...", flush=True)

    # Ensure directory exists
    os.makedirs("/app/data", exist_ok=True)

    for message in consumer:
        data = message.value
        file_exists = os.path.isfile(CSV_FILE)
        
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['task', 'solution', 'review'])
            if not file_exists:
                writer.writeheader()
            writer.writerow(data)
        
        print(f"📁 Archived task: {data['task'][:30]}...", flush=True)