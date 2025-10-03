import json
import numpy as np
from pathlib import Path
from vercel import Response

# Load telemetry data
DATA_PATH = Path(__file__).parent.parent / "q-vercel-latency.json"
with DATA_PATH.open() as f:
    DATA = json.load(f)

def handler(request):
    headers = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"}

    if request.method != "POST":
        return Response(json.dumps({"error": "Only POST allowed"}), status=405, headers=headers)

    try:
        body = request.json()
    except Exception:
        return Response(json.dumps({"error": "Invalid JSON"}), status=400, headers=headers)

    regions = body.get("regions", [])
    threshold_ms = body.get("threshold_ms", 180)

    result = {}
    for region in regions:
        items = [r for r in DATA if r.get("region") == region]
        if not items:
            result[region] = {"avg_latency": None, "p95_latency": None, "avg_uptime": None, "breaches": 0}
            continue

        latencies = [r["latency_ms"] for r in items]
        uptimes = [r["uptime_pct"] for r in items]

        avg_latency = float(sum(latencies) / len(latencies))
        p95_latency = float(np.percentile(latencies, 95))
        avg_uptime = float(sum(uptimes) / len(uptimes))
        breaches = sum(1 for v in latencies if v > threshold_ms)

        result[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 3),
            "breaches": int(breaches),
        }

    return Response(json.dumps(result), headers=headers)
