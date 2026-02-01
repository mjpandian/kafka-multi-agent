import json
import time
from kafka import KafkaProducer

# Configuration
KAFKA_BROKER = 'localhost:9092'  # Ensure ports: ["9092:9092"] is in your docker-compose
TOPIC = 'ai_topic'

def run_stress_test():
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        print(f"🌊 Flooding {TOPIC} with 50 tasks...")

        for i in range(1, 51):
            task_msg = {
                "task": f"STRESS TEST {i}: Write a complex algorithm for sorting a linked list."
            }
            producer.send(TOPIC, task_msg)
            if i % 10 == 0:
                print(f"📤 Sent {i}/50 tasks...")
        
        producer.flush()
        print("✅ Stress test injection complete!")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_stress_test()