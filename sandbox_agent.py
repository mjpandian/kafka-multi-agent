import os, json, time, asyncio, subprocess
from kafka import KafkaConsumer, KafkaProducer
from utils.telemetry_utils import TelemetryLogger
from skills.memory_skill import MemorySkill

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

def clean_code(code):
    """Strips markdown code blocks if present."""
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0]
    elif "```" in code:
        code = code.split("```")[1].split("```")[0]
    return code.strip()

async def run_code_safely(code):
    code = clean_code(code)
    try:
        # Use asyncio.create_subprocess_exec for non-blocking execution
        proc = await asyncio.create_subprocess_exec(
            'python', '-c', code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            return {
                "success": proc.returncode == 0,
                "output": stdout.decode().strip() if proc.returncode == 0 else stderr.decode().strip()
            }
        except asyncio.TimeoutError:
            proc.kill()
            return {"success": False, "output": "Execution timed out"}
    except Exception as e:
        return {"success": False, "output": f"Execution Error: {str(e)}"}

async def main():
    consumer = KafkaConsumer(
        'ai_solutions',
        bootstrap_servers=KAFKA_BROKER,
        api_version=(3, 5, 0),
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        api_version=(3, 5, 0),
        value_serializer=lambda x: json.dumps(x).encode('utf-8')
    )
    
    telemetry = TelemetryLogger("sandbox")
    memory = MemorySkill("sandbox_agent")

    telemetry.log("🧪 Smart Sandbox is active.")
    telemetry.log_event("agent_started")

    for message in consumer:
        try:
            data = message.value
            task = data['task']
            code = data['solution']
            
            telemetry.log(f"🔬 Testing code for: {task[:30]}...")
            
            start_time = time.time()
            execution = await run_code_safely(code)
            latency = (time.time() - start_time) * 1000
            
            telemetry.log_metric("execution_latency", latency)
            telemetry.log_metric("execution_success", 1 if execution['success'] else 0)

            # Always notify the dashboard via ai_verified_solutions
            producer.send('ai_verified_solutions', {
                **data, 
                "success": execution['success'],
                "exec_output": execution['output']
            })

            if execution['success']:
                telemetry.log("✅ Code Passed! Verified results published.")
            else:
                telemetry.log(f"❌ Code Failed: {execution['output'][:100]}")
                memory.add_memory(f"Failure in '{task}': {execution['output']}", metadata={"type": "failure_log"})
                telemetry.log_event("learning_event", {"type": "failure_avoidance", "content": f"Avoided: {execution['output'][:50]}"})
                
                producer.send('ai_topic', {
                    "task": f"FIX THIS CODE: {task}\nError: {execution['output']}"
                })
        except Exception as e:
            telemetry.log(f"💀 Critical Sandbox Loop Error: {e}")
            time.sleep(1) # Prevent tight crash loop

if __name__ == "__main__":
    asyncio.run(main())