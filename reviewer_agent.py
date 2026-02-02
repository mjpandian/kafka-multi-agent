import os, json, time
from kafka import KafkaConsumer, KafkaProducer
from openai import OpenAI

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
IN_TOPIC = "ai_solutions"
OUT_TOPIC = "ai_reviews"
OLLAMA_URL = os.getenv("OLLAMA_URL")
from utils.telemetry_utils import TelemetryLogger
telemetry = TelemetryLogger("reviewer")

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
            telemetry.log(f"⌛ Reviewer waiting for Kafka... {e}")
            time.sleep(5)

client = OpenAI(base_url=OLLAMA_URL, api_key="ollama")

if __name__ == "__main__":
    consumer, producer = initialize_kafka()
    telemetry.log("🕵️ Reviewer Agent is active.")
    
    for message in consumer:
        solution_data = message.value
        code = solution_data.get('solution', '')
        
        telemetry.log(f"🧐 Reviewing code for: {solution_data['task'][:30]}...")
        
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
        telemetry.log(f"✅ Review completed and sent to {OUT_TOPIC}")