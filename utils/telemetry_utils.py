import os
import json
import time
from kafka import KafkaProducer

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

class TelemetryLogger:
    def __init__(self, agent_name):
        self.agent_name = agent_name
        self.producer = None
        self._initialize_producer()

    def _initialize_producer(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                api_version=(3, 5, 0),
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
        except Exception as e:
            print(f"⚠️ Telemetry fallback: {e}")

    def log_metric(self, metric_type, value, extra=None):
        payload = {
            "agent": self.agent_name,
            "type": metric_type,
            "value": value,
            "timestamp": time.time(),
            "extra": extra or {}
        }
        
        if self.producer:
            try:
                self.producer.send("ai_telemetry", payload)
            except Exception as e:
                print(f"❌ Telemetry fail: {e}")
        else:
            print(f"📊 [LOCAL TELEMETRY] {payload}")

    def log_event(self, event_name, data=None):
        self.log_metric("event", event_name, extra=data)

    def log(self, message):
        """Sends a log message to the telemetry topic."""
        payload = {
            "agent": self.agent_name,
            "type": "log",
            "message": message,
            "timestamp": time.time()
        }
        if self.producer:
            try:
                self.producer.send("ai_telemetry", payload)
            except Exception as e:
                print(f"❌ Log fail: {e}")
        print(f"[{self.agent_name}] {message}")
