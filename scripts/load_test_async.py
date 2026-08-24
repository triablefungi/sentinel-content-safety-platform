import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass

import httpx

TERMINAL_STATES = {"succeeded", "failed"}


@dataclass(frozen=True)
class Submission:
    job_id: str
    latency_ms: float


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile_value)
    return ordered[index]


async def submit_job(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    index: int,
) -> Submission:
    payload = {
        "request_id": f"load-test-{time.time_ns()}-{index}",
        "text": "Thank you for sharing your perspective.",
    }
    async with semaphore:
        started = time.perf_counter()
        response = await client.post("/v1/moderation/jobs", json=payload)
        latency_ms = (time.perf_counter() - started) * 1_000
    response.raise_for_status()
    return Submission(job_id=response.json()["job_id"], latency_ms=latency_ms)


async def wait_for_terminal_jobs(
    client: httpx.AsyncClient,
    job_ids: list[str],
    timeout_seconds: float,
) -> dict[str, int]:
    deadline = time.monotonic() + timeout_seconds
    pending = set(job_ids)
    counts = {"succeeded": 0, "failed": 0}
    while pending and time.monotonic() < deadline:
        batch = list(pending)
        responses = await asyncio.gather(
            *(client.get(f"/v1/moderation/jobs/{job_id}") for job_id in batch)
        )
        for job_id, response in zip(batch, responses, strict=True):
            response.raise_for_status()
            state = response.json()["state"]
            if state in TERMINAL_STATES:
                counts[state] += 1
                pending.remove(job_id)
        if pending:
            await asyncio.sleep(0.25)
    counts["incomplete"] = len(pending)
    return counts


async def benchmark(args: argparse.Namespace) -> int:
    semaphore = asyncio.Semaphore(args.concurrency)
    limits = httpx.Limits(max_connections=args.concurrency)
    timeout = httpx.Timeout(30.0)
    async with httpx.AsyncClient(
        base_url=args.base_url,
        limits=limits,
        timeout=timeout,
    ) as client:
        started = time.perf_counter()
        submissions = await asyncio.gather(
            *(submit_job(client, semaphore, index) for index in range(args.requests))
        )
        submission_seconds = time.perf_counter() - started
        counts = await wait_for_terminal_jobs(
            client,
            [submission.job_id for submission in submissions],
            args.terminal_timeout,
        )
        total_seconds = time.perf_counter() - started

    latencies = [submission.latency_ms for submission in submissions]
    print(f"Accepted jobs: {len(submissions)}")
    print(f"Succeeded: {counts['succeeded']}")
    print(f"Failed: {counts['failed']}")
    print(f"Incomplete at timeout: {counts['incomplete']}")
    print(f"Submission throughput: {len(submissions) / submission_seconds:.2f} jobs/s")
    print(f"Terminal throughput: {len(submissions) / total_seconds:.2f} jobs/s")
    print(f"Mean submission latency: {statistics.fmean(latencies):.2f} ms")
    print(f"p50 submission latency: {percentile(latencies, 0.50):.2f} ms")
    print(f"p95 submission latency: {percentile(latencies, 0.95):.2f} ms")
    return 1 if counts["incomplete"] else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark the asynchronous moderation API")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--terminal-timeout", type=float, default=120.0)
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1 or args.terminal_timeout <= 0:
        parser.error("requests, concurrency, and terminal-timeout must be positive")
    return args


if __name__ == "__main__":
    raise SystemExit(asyncio.run(benchmark(parse_args())))
