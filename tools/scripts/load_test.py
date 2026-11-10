"""Small load test of the non-AI paths (N8). It makes no AI calls and writes nothing but one login audit.

Usage: python tools/scripts/load_test.py <base_url> <username> <password> [requests] [concurrency]
"""
import asyncio
import statistics
import sys
import time

import httpx


async def worker(client, queue, results):
    while True:
        try:
            path = queue.get_nowait()
        except asyncio.QueueEmpty:
            return
        start = time.perf_counter()
        try:
            status = (await client.get(path)).status_code
        except httpx.HTTPError:
            status = 0
        results.append((path, status, (time.perf_counter() - start) * 1000))


async def main(base, user, password, total, concurrency):
    async with httpx.AsyncClient(base_url=base, timeout=30) as client:
        login = await client.post("/api/auth/login", json={"username": user, "password": password})
        login.raise_for_status()
        client.headers["Authorization"] = f"Bearer {login.json()['token']}"
        paths = ["/health", "/api/cases", "/api/metrics"]
        queue = asyncio.Queue()
        for i in range(total):
            queue.put_nowait(paths[i % len(paths)])
        results = []
        started = time.perf_counter()
        await asyncio.gather(*(worker(client, queue, results) for _ in range(concurrency)))
        seconds = time.perf_counter() - started
    print(f"{total} requests, {concurrency} at a time, {seconds:.1f}s, {total / seconds:.0f} requests/s")
    for path in paths:
        rows = [r for r in results if r[0] == path]
        ms = sorted(r[2] for r in rows)
        errors = sum(1 for r in rows if r[1] != 200)
        print(f"{path}: errors {errors}/{len(rows)}, median {statistics.median(ms):.0f} ms, "
              f"p95 {ms[int(len(ms) * 0.95) - 1]:.0f} ms")


if __name__ == "__main__":
    a = sys.argv
    asyncio.run(main(a[1], a[2], a[3], int(a[4]) if len(a) > 4 else 300, int(a[5]) if len(a) > 5 else 10))
