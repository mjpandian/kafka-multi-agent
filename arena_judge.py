import os, json, time, collections
from kafka import KafkaConsumer, KafkaProducer
from openai import OpenAI
from utils.telemetry_utils import TelemetryLogger

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
OLLAMA_URL = os.getenv("OLLAMA_URL")
telemetry = TelemetryLogger("judge")
client = OpenAI(base_url=OLLAMA_URL, api_key="ollama")

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
qdrant = QdrantClient(host=QDRANT_HOST, port=6333)
MODEL_NAME = os.getenv("ARENA_JUDGE_MODEL", "gemma3:1b")

# Initialize Qdrant Collection
try:
    qdrant.get_collection("arena_memory")
except:
    qdrant.create_collection(
        collection_name="arena_memory",
        vectors_config=VectorParams(size=1, distance=Distance.COSINE), # Placeholder vector
    )

def initialize_kafka():
    while True:
        try:
            consumer = KafkaConsumer(
                'arena_proposals',
                bootstrap_servers=KAFKA_BROKER,
                api_version=(3, 5, 0),
                group_id='judge-group',
                auto_offset_reset='earliest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                api_version=(3, 5, 0),
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            return consumer, producer
        except Exception as e:
            telemetry.log(f"⌛ Judge waiting for Kafka... {e}")
            time.sleep(5)

if __name__ == "__main__":
    consumer, producer = initialize_kafka()
    telemetry.log("⚖️ Arena Judge (Agentic AI Expert) is active.")
    
    # Store proposals by task_id and round
    proposals = collections.defaultdict(list)

    for message in consumer:
        msg = message.value
        task_id = msg['task_id']
        solver_id = msg['solver_id']
        round_num = msg['round']
        
        proposals[(task_id, round_num)].append(msg)
        telemetry.log(f"📥 Received proposal from {solver_id} for {task_id} (Round {round_num})")

        # Threshold for judging
        if len(proposals[(task_id, round_num)]) >= 1:
            telemetry.log(f"🤔 1 Proposal(s) received for {task_id} (Round {round_num}). Judging...")
            
            competitors_str = "\n\n".join([f"--- SOLVER: {p['solver_id']} ---\n{p['content']}" for p in proposals[(task_id, round_num)]])
            
            rubric_prompt = f"""Evaluate the following solution(s) using this strict rubric:
1. Accuracy (0-10): How factually correct is the response?
2. Persona Adherence (0-10): How well does it match the expert tone?
3. Reasoning (0-10): Is the logic sound and detailed?

Finally, provide a 'Consolidator Feedback' for improvement and declare a status: 'refine' or 'complete'.

PROPOSALS:
{competitors_str}"""
            
            print(f"DEBUG: Judge starting evaluation for {task_id}...", flush=True)
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": rubric_prompt}]
            )
            
            evaluation = resp.choices[0].message.content
            print(f"DEBUG: Evaluation finished for {task_id}.", flush=True)
            telemetry.log(f"⚖️ Evaluation Complete for {task_id}")

            status = 'complete' if ('COMPLETE' in evaluation.upper() or round_num >= 3) else 'refine'

            # If complete, persist the best solution to memory
            if status == 'complete':
                telemetry.log(f"💾 Persisting memory for {task_id}")
                # Simple placeholder for vector (would normally use embeddings)
                winner_content = proposals[(task_id, round_num)][0]['content']
                qdrant.upsert(
                    collection_name="arena_memory",
                    points=[PointStruct(id=int(time.time()), vector=[0.5], payload={"task_id": task_id, "solution": winner_content})]
                )

            # Send feedback back to the arena
            producer.send('arena_feedback', {
                'task_id': task_id,
                'round': round_num,
                'feedback': evaluation,
                'status': status
            })
            
            # Agentic Telemetry: Emit Reward Payload
            telemetry.log(f"🏆 System Reward for {task_id}: {status.upper()}")
            producer.send('ai_telemetry', {
                'type': 'reward_payload',
                'task_id': task_id,
                'agent': 'judge',
                'status': status,
                'metrics': {
                    'round': round_num,
                    'is_complete': status == 'complete'
                }
            })
            producer.flush()
            telemetry.log(f"📤 Feedback sent for {task_id}")
