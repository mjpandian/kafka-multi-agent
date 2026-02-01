import os, json, time
from kafka import KafkaConsumer, KafkaProducer
from openai import OpenAI

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
IN_TOPIC = "ai_solutions"
OUT_TOPIC = "ai_reviews"
OLLAMA_URL = os.getenv("OLLAMA_URL")

def initialize_kafka():
    while True:
        try:
            consumer = KafkaConsumer(
                IN_TOPIC,
                bootstrap_servers=KAFKA_BROKER,
                api_version=(3, 5, 0),
                group_id='reviewer-group',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                api_version=(3, 5, 0),
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            return consumer, producer
        except Exception as e:
            print(f"⌛ Reviewer waiting for Kafka... {e}", flush=True)
            time.sleep(5)

client = OpenAI(base_url=OLLAMA_URL, api_key="ollama")

if __name__ == "__main__":
    consumer, producer = initialize_kafka()
    print("🕵️ Reviewer Agent is active. Standing by for code submissions...", flush=True)
    
    for message in consumer:
        solution_data = message.value
        code = solution_data.get('solution', '')
        
        print(f"🧐 Reviewing code for task: {solution_data['task'][:50]}...", flush=True)
        
        resp = client.chat.completions.create(
            model="gemma3:1b",
            messages=[{"role": "user", "content": f"Review this code for bugs or efficiency. Be concise: {code}"}]
        )
        
        review = resp.choices[0].message.content
        producer.send(OUT_TOPIC, {
            'task': solution_data['task'],
            'solution': code,
            'review': review
        })
        print(f"✅ Review completed and sent to {OUT_TOPIC}", flush=True)