
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


BASE_URL = "http://127.0.0.1:8001"


# ============================================================
# ENDPOINTS TO TEST
# ============================================================

ENDPOINTS = [
    "/api/v1/health",
    "/api/v1/companies",
    "/api/v1/companies/TCS",
    "/api/v1/companies/TCS/pl",
    "/api/v1/companies/TCS/bs",
    "/api/v1/companies/TCS/cashflow",
    "/api/v1/companies/TCS/ratios",
    "/api/v1/companies/TCS/tearsheet",
    "/api/v1/screener",
    "/api/v1/sectors",
    "/api/v1/sectors/Industrials/companies",
    "/api/v1/peers/Private%20Banks",
    "/api/v1/companies/HDFCBANK/peers/compare",
    "/api/v1/market-cap/TCS",
    "/api/v1/portfolio/stats",
    "/api/v1/companies/TCS/documents",
]


# ============================================================
# BASIC RESPONSE TEST
# ============================================================

def test_health_response_time():
    start = time.perf_counter()

    response = requests.get(
        f"{BASE_URL}/api/v1/health",
        timeout=10,
    )

    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 2.0


# ============================================================
# SINGLE-ENDPOINT PERFORMANCE
# ============================================================

def test_endpoint_performance():
    results = []

    for endpoint in ENDPOINTS:
        start = time.perf_counter()

        response = requests.get(
            f"{BASE_URL}{endpoint}",
            timeout=10,
        )

        elapsed = time.perf_counter() - start

        assert response.status_code == 200

        results.append(
            {
                "endpoint": endpoint,
                "status": response.status_code,
                "response_time": elapsed,
            }
        )

    print("\n\nEndpoint Performance")
    print("=" * 70)

    for result in results:
        print(
            f"{result['endpoint']:<50} "
            f"{result['response_time']:.4f}s"
        )

    average = statistics.mean(
        result["response_time"]
        for result in results
    )

    maximum = max(
        result["response_time"]
        for result in results
    )

    print("-" * 70)
    print(f"Average response time : {average:.4f}s")
    print(f"Maximum response time : {maximum:.4f}s")

    assert average < 2.0
    assert maximum < 5.0


# ============================================================
# CONCURRENT LOAD TEST
# ============================================================

def request_endpoint(endpoint):
    start = time.perf_counter()

    try:
        response = requests.get(
            f"{BASE_URL}{endpoint}",
            timeout=10,
        )

        elapsed = time.perf_counter() - start

        return {
            "endpoint": endpoint,
            "status": response.status_code,
            "response_time": elapsed,
            "success": response.status_code == 200,
        }

    except Exception as exc:
        elapsed = time.perf_counter() - start

        return {
            "endpoint": endpoint,
            "status": None,
            "response_time": elapsed,
            "success": False,
            "error": str(exc),
        }


def test_concurrent_load():
    requests_per_endpoint = 5

    workload = []

    for endpoint in ENDPOINTS:
        for _ in range(requests_per_endpoint):
            workload.append(endpoint)

    start = time.perf_counter()

    results = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(request_endpoint, endpoint)
            for endpoint in workload
        ]

        for future in as_completed(futures):
            results.append(future.result())

    total_time = time.perf_counter() - start

    total_requests = len(results)
    successful_requests = sum(
        result["success"]
        for result in results
    )

    failed_requests = total_requests - successful_requests

    response_times = [
        result["response_time"]
        for result in results
    ]

    average = statistics.mean(response_times)
    maximum = max(response_times)

    success_rate = (
        successful_requests / total_requests
    ) * 100

    throughput = (
        total_requests / total_time
        if total_time > 0
        else 0
    )

    print("\n\nConcurrent Load Test")
    print("=" * 70)
    print(f"Total requests       : {total_requests}")
    print(f"Successful requests  : {successful_requests}")
    print(f"Failed requests      : {failed_requests}")
    print(f"Success rate         : {success_rate:.2f}%")
    print(f"Total execution time : {total_time:.4f}s")
    print(f"Average response     : {average:.4f}s")
    print(f"Maximum response     : {maximum:.4f}s")
    print(f"Throughput           : {throughput:.2f} requests/sec")

    assert total_requests == 80
    assert failed_requests == 0
    assert success_rate == 100.0
    assert average < 3.0
    assert maximum < 10.0


# ============================================================
# REPEATED HEALTH CHECK
# ============================================================

def test_repeated_health_requests():
    response_times = []

    for _ in range(20):
        start = time.perf_counter()

        response = requests.get(
            f"{BASE_URL}/api/v1/health",
            timeout=10,
        )

        elapsed = time.perf_counter() - start

        assert response.status_code == 200

        response_times.append(elapsed)

    average = statistics.mean(response_times)
    maximum = max(response_times)

    print("\n\nRepeated Health Requests")
    print("=" * 70)
    print(f"Requests             : 20")
    print(f"Average response     : {average:.4f}s")
    print(f"Maximum response     : {maximum:.4f}s")

    assert average < 1.0
    assert maximum < 2.0

