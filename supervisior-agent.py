import os, time
from kafka import KafkaAdminClient, TopicPartition, KafkaConsumer

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

def monitor():
    admin = None
    consumer = None
    
    while True:
        try:
            if not admin:
                admin = KafkaAdminClient(bootstrap_servers=KAFKA_BROKER, api_version=(3, 5, 0))
            if not consumer:
                consumer = KafkaConsumer(bootstrap_servers=KAFKA_BROKER, api_version=(3, 5, 0))
            
            tp = TopicPartition('ai_topic', 0)
            # Check if topic exists yet
            if 'ai_topic' in consumer.topics():
                end_offsets = consumer.end_offsets([tp])
                producer_pos = end_offsets[tp]
                
                grp_offsets = admin.list_consumer_group_offsets('agent-b-group')
                consumer_pos = grp_offsets[tp].offset if tp in grp_offsets else 0
                
                print(f"📊 MONITOR: Producer @ {producer_pos} | Consumer @ {consumer_pos} | LAG: {producer_pos - consumer_pos}", flush=True)
            else:
                print("🔎 Monitor: Waiting for 'ai_topic' to be created...", flush=True)
                
        except Exception as e:
            print(f"⌛ Supervisor waiting for Kafka... ({e})", flush=True)
            admin = None # Reset connection
            consumer = None
            
        time.sleep(10)

if __name__ == "__main__":
    monitor()
    