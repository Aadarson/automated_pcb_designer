import asyncio
from backend.jobs.design_worker import _execute_pipeline

async def test_zero_error_pipeline():
    request_dict = {
        "project_name": "TestHeal",
        "prompt": "an arduino nano with a motor driver and 4 leds and screw terminals",
        "board": {
            "width_mm": 20.0,
            "height_mm": 20.0,
            "layers": 2,
            "outline": "rect"
        },
        "components": [],
        "nets": [],
        "rules": {},
        "routing_goals": {}
    }
    job_id = "test-job-id-1234"
    
    try:
        print("Starting pipeline test...")
        await _execute_pipeline(job_id, request_dict)
        print("Pipeline execution completed without unhandled exceptions.")
    except Exception as e:
        print(f"PIPELINE CRASHED: {e}")

if __name__ == "__main__":
    asyncio.run(test_zero_error_pipeline())
