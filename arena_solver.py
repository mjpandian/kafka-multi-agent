import os, json, time
from kafka import KafkaConsumer, KafkaProducer
from openai import OpenAI
from utils.telemetry_utils import TelemetryLogger

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
OLLAMA_URL = os.getenv("OLLAMA_URL")
SOLVER_ID = os.getenv("SOLVER_ID", "anonymous-solver")
SOLVER_PERSONA = os.getenv("SOLVER_PERSONA", "General Expert")
MODEL_NAME = os.getenv("ARENA_SOLVER_MODEL", "gemma3:1b")

telemetry = TelemetryLogger(f"solver-{SOLVER_ID}")
client = OpenAI(base_url=OLLAMA_URL, api_key="ollama")

def initialize_kafka():
    while True:
        try:
            consumer = KafkaConsumer(
                'arena_tasks', 'arena_feedback',
                bootstrap_servers=KAFKA_BROKER,
                api_version=(3, 5, 0),
                group_id=f'solver-group-{SOLVER_ID}',
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
            telemetry.log(f"⌛ Solver waiting for Kafka... {e}")
            time.sleep(5)

if __name__ == "__main__":
    consumer, producer = initialize_kafka()
    telemetry.log(f"⚔️ Solver [{SOLVER_ID}] with Persona [{SOLVER_PERSONA}] is active.")
    
    # Staggered Start to prevent Ollama memory spikes
    delay = {"alpha": 0, "beta": 5, "gamma": 10}.get(SOLVER_ID, 0)
    if delay > 0:
        telemetry.log(f"⏳ Staggering start: Waiting {delay}s...")
        time.sleep(delay)
    
    # Track state for refinement
    active_tasks = {}

    for message in consumer:
        msg = message.value
        topic = message.topic
        
        if topic == 'arena_tasks':
            task_id = msg['task_id']
            prompt = msg['prompt']
            telemetry.log(f"📥 New Task Received: {task_id}")
            
            print(f"DEBUG: Solver starting inference for {task_id}...", flush=True)
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": f"You are an expert with the following persona: {SOLVER_PERSONA}. Provide a detailed and expert solution."},
                    {"role": "user", "content": prompt}
                ]
            )
            draft_content = resp.choices[0].message.content
            print(f"DEBUG: Draft generated for {task_id}. Starting self-reflexion...", flush=True)
            
            # Agentic Self-Reflexion Layer
            reflexion_prompt = f"Review your own solution for quality, potential errors, and persona adherence. Output a refined and superior version of your response.\n\nDRAFT:\n{draft_content}"
            resp_reflexion = client.chat.completions.create(
                model="gemma3:1b",
                messages=[
                    {"role": "system", "content": f"You are a critical reviewer of your own work as {SOLVER_PERSONA}."},
                    {"role": "user", "content": reflexion_prompt}
                ]
            )
            content = resp_reflexion.choices[0].message.content
            print(f"DEBUG: Inference and Self-Reflexion finished for {task_id}.", flush=True)
            
            active_tasks[task_id] = {"prompt": prompt, "history": [content]}
            
            producer.send('arena_proposals', {
                'task_id': task_id,
                'solver_id': SOLVER_ID,
                'persona': SOLVER_PERSONA,
                'round': 1,
                'content': content
            })
            producer.flush()
            telemetry.log(f"📤 Proposal (Round 1) sent for {task_id}")

        elif topic == 'arena_feedback':
            task_id = msg['task_id']
            if task_id in active_tasks:
                feedback = msg['feedback']
                telemetry.log(f"🔄 Received Feedback for {task_id}")
                
                resp = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": f"You are an expert with the following persona: {SOLVER_PERSONA}. Refine your previous solution based on the feedback provided."},
                        {"role": "user", "content": f"Original Task: {active_tasks[task_id]['prompt']}\n\nYour Previous Answer: {active_tasks[task_id]['history'][-1]}\n\nJudge Feedback: {feedback}"}
                    ]
                )
                refined_content = resp.choices[0].message.content
                active_tasks[task_id]['history'].append(refined_content)

                producer.send('arena_proposals', {
                    'task_id': task_id,
                    'solver_id': SOLVER_ID,
                    'persona': SOLVER_PERSONA,
                    'round': len(active_tasks[task_id]['history']),
                    'content': refined_content
                })
                producer.flush()
                telemetry.log(f"📤 Refined Proposal sent for {task_id}")
