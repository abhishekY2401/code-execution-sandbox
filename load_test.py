import asyncio
import httpx
import time
import random

# Configuration
BASE_URL = "http://localhost:5000"
API_URL = BASE_URL + "/submissions"  # Update with your endpoint
CONCURRENT_USERS = 50  # Number of parallel request tasks
TOTAL_SUBMISSIONS = 500  # Cap test to 500 submissions for this run

# A heavier CPU/memory stress script (matrix multiplication + primes)
COMPLEX_CODE = """
import math

# Build a medium-sized matrix and multiply it for CPU+memory work.
N = 200
A = [[(i + j) % 100 for j in range(N)] for i in range(N)]
B = [[(i * j) % 100 for j in range(N)] for i in range(N)]

# Multiply A * B
C = [[0]*N for _ in range(N)]
for i in range(N):
    for j in range(N):
        s = 0
        for k in range(N):
            s += A[i][k] * B[k][j]
        C[i][j] = s

# Do an additional compute-heavy task for good measure
primes = []
for n in range(2, 12000):
    is_p = True
    for d in range(2, int(math.sqrt(n)) + 1):
        if n % d == 0:
            is_p = False
            break
    if is_p:
        primes.append(n)

print(f"Matrix[0][0]={C[0][0]}, primes={len(primes)} (last={primes[-1]})")
"""

async def submit_job(client, user_id):
    payload = {
        "language": "python",
        "code": COMPLEX_CODE,
    }
    try:
        start_time = time.time()
        response = await client.post(API_URL, json=payload, timeout=10)
        duration = time.time() - start_time
        return response.status_code, duration
    except Exception as e:
        return "ERROR", 0

async def main():
    limits = httpx.Limits(max_connections=CONCURRENT_USERS)
    async with httpx.AsyncClient(limits=limits) as client:
        print(f"🚀 Starting load test: {TOTAL_SUBMISSIONS} submissions...")

        start_overall = time.time()

        # Using a semaphore to control concurrency
        semaphore = asyncio.Semaphore(CONCURRENT_USERS)

        async def sem_task(i):
            async with semaphore:
                return await submit_job(client, i)

        # Track progress as requests complete
        results = []
        completed = 0
        last_report = time.time()
        report_every = max(1, TOTAL_SUBMISSIONS // 10)

        for coro in asyncio.as_completed([sem_task(i) for i in range(TOTAL_SUBMISSIONS)]):
            result = await coro
            results.append(result)
            completed += 1

            # Periodic progress logging
            if completed % report_every == 0 or completed == TOTAL_SUBMISSIONS:
                elapsed = time.time() - start_overall
                print(f"  ✅ Completed: {completed}/{TOTAL_SUBMISSIONS} (elapsed: {elapsed:.1f}s)")

        # Trigger batch processing
        print("Triggering batch processing...")
        try:
            response = await client.post(BASE_URL + "/process-batches", timeout=10)
            print(f"Batch processing response: {response.status_code}")
        except Exception as e:
            print(f"Error triggering batch processing: {e}")

        end_overall = time.time()

        # Stats calculation
        successes = [r for r in results if r[0] == 200 or r[0] == 202]
        errors = [r for r in results if r[0] == "ERROR" or r[0] >= 400]
        avg_time = sum(r[1] for r in successes) / len(successes) if successes else 0

        print("\n--- Load Test Results ---")
        print(f"Total Time: {end_overall - start_overall:.2f}s")
        print(f"Successes: {len(successes)}")
        print(f"Failures: {len(errors)}")
        print(f"Avg Latency (API call): {avg_time:.2f}s")
        print(f"Throughput: {len(successes) / (end_overall - start_overall):.2f} req/s")

if __name__ == "__main__":
    asyncio.run(main())