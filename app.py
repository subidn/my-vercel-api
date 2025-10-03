# api/metrics.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from pathlib import Path
import math, json

app = FastAPI()

# Enable CORS for POST requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],   # only POST required by your spec
    allow_headers=["*"],
)

class Query(BaseModel):
    regions: List[str]
    threshold_ms: float

# robust path: project root (api/ is one level down)
BASE = Path(__file__).resolve().parents[1]
DATA_FILE = BASE / "q-vercel-latency.json"

def p95_nearest_rank(values):
    if not values:
        return None
    vals = sorted(values)
    n = len(vals)
    idx = math.ceil(0.95 * n) - 1
    idx = max(0, min(idx, n - 1))
    return vals[idx]

@app.post("/")
async def metrics(query: Query) -> Dict[str, Any]:
    if not DATA_FILE.exists():
        raise HTTPException(status_code=500, detail=f"Telemetry file not found at {DATA_FILE}")

    with open(DATA_FILE, "r") as fh:
        data = json.load(fh)

    results: Dict[str, Any] = {}
    for region in query.regions:
        recs = [r for r in data if r.get("region") == region]
        lat = [r["latency_ms"] for r in recs]
        up = [r["uptime_pct"] for r in recs]

        if not recs:
            results[region] = {
                "avg_latency": None,
                "p95_latency": None,
                "avg_uptime": None,
                "breaches": 0
            }
            continue

        avg_latency = sum(lat) / len(lat)
        p95 = p95_nearest_rank(lat)
        avg_uptime = sum(up) / len(up)
        breaches = sum(1 for v in lat if v > query.threshold_ms)

        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95, 2) if p95 is not None else None,
            "avg_uptime": round(avg_uptime, 3),
            "breaches": int(breaches)
        }

    return results
