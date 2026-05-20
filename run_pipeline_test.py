import asyncio
from backend.jobs.design_worker import _execute_pipeline
from backend.core.redis_client import redis_client

class MockRedis:
    async def publish_event(self, job_id, data):
        if data.get("step") == "done":
            print("\n!!! PIPELINE COMPLETED !!!")
            print("PLACEMENTS:")
            if "result" in data and "placement_score" in data["result"]:
                print(f"Placement Score: {data['result']['placement_score']}")
            
            if "result" in data and "drc_report" in data["result"]:
                passed = data["result"]["drc_report"]["passed"]
                violations = data["result"]["drc_report"]["violations"]
                print(f"DRC Passed? {passed}")
                print(f"Total DRC Violations: {len(violations)}")
                if violations:
                    print("Sample of violations:")
                    for idx, v in enumerate(violations[:5]):
                        print(f" - {v.get('rule')}: {v.get('description')}")
        else:
            print(f"Progress Step: {data.get('step')} ({data.get('progress')}%)")

redis_client.publish_event = MockRedis().publish_event

async def local_run():
    request_dict = {
        "project_name": "AntigravityTest",
        "prompt": "Arduino Uno clone with a ch340g, 4 leds, 2 resistors, and a usb c port.",
        "board": {
            "width_mm": 60,
            "height_mm": 60,
            "layers": 2,
            "outline": "rect"
        },
        "components": [],
        "nets": []
    }
    print("Executing pipeline locally...")
    await _execute_pipeline("test-job-9999", request_dict)
    
    # Cancel background tasks (like the 100k step RL background training) so the script exits instantly
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]

if __name__ == "__main__":
    asyncio.run(local_run())
