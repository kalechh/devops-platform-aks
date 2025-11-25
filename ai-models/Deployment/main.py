from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np
import logging
from typing import List, Dict, Any, Optional
import uvicorn
from datetime import datetime, timedelta
import os
import httpx
import asyncio
from prometheus_client import CollectorRegistry, Gauge, Counter, generate_latest
import json

# ---------------------------------------------------
# Logging configuration
# ---------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------
# FastAPI application
# ---------------------------------------------------
app = FastAPI(
    title="Kubernetes Pod Autoscaling Predictor with Prometheus Integration",
    description="API that pulls metrics from Prometheus, makes predictions, and provides scaling decisions to KEDA",
    version="1.1.0"  # bumped
)

# ---------------------------------------------------
# Prometheus custom metrics
# ---------------------------------------------------
registry = CollectorRegistry()
prediction_counter = Counter('prediction_requests_total', 'Total prediction requests', registry=registry)
prediction_gauge = Gauge('predicted_pod_count', 'Currently predicted pod count', registry=registry)
model_confidence_gauge = Gauge('model_confidence', 'Model prediction confidence', registry=registry)

# ---------------------------------------------------
# Environment configuration
# ---------------------------------------------------
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://monitoring-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090")
TARGET_NAMESPACE = os.getenv("TARGET_NAMESPACE", "hamzadevops")
TARGET_DEPLOYMENT = os.getenv("TARGET_DEPLOYMENT", "eventmanagement")
MODEL_PATH = os.getenv("MODEL_PATH", "/app/model/pod_predictor.pkl")
MODEL_METADATA_PATH = os.getenv("MODEL_METADATA_PATH", "/app/model/metadata.json")

# ---------------------------------------------------
# Global runtime objects
# ---------------------------------------------------
model = None  # ML model loaded at startup
expected_feature_names: List[str] = []  # order expected by the model

# ---------------------------------------------------
# Pydantic models (schema)
# ---------------------------------------------------
class PrometheusMetrics(BaseModel):
    cpu_usage: float
    memory_usage: float
    request_rate: float
    queue_length: float
    response_time: float
    active_connections: float

class PredictionResponse(BaseModel):
    predicted_pod_count: int
    confidence: float
    timestamp: str
    metrics_used: PrometheusMetrics
    model_version: str

class KEDAMetricResponse(BaseModel):
    metric_value: int
    timestamp: str

# ---------------------------------------------------
# Prometheus HTTP client helper
# ---------------------------------------------------
class PrometheusClient:
    def __init__(self, prometheus_url: str):
        self.prometheus_url = prometheus_url
        self.client = httpx.AsyncClient(timeout=10.0)

    async def query_metric(self, query: str) -> float:
        """Query a single metric from Prometheus"""
        try:
            response = await self.client.get(f"{self.prometheus_url}/api/v1/query", params={"query": query})
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "success" and data["data"]["result"]:
                return float(data["data"]["result"][0]["value"][1])
        except Exception as ex:
            logger.error(f"Prometheus query failed for '{query}': {ex}")
        return 0.0  # graceful fallback

    async def get_workload_metrics(self) -> PrometheusMetrics:
        """Collect all base metrics we know how to compute in real‑time"""
        queries = {
            "cpu_usage": f'avg(rate(container_cpu_usage_seconds_total{{namespace="{TARGET_NAMESPACE}", pod=~"{TARGET_DEPLOYMENT}.*"}}[5m])) * 100',
            "memory_usage": f'avg(container_memory_working_set_bytes{{namespace="{TARGET_NAMESPACE}", pod=~"{TARGET_DEPLOYMENT}.*"}}) / 1024 / 1024',
            "request_rate": f'sum(rate(http_requests_total{{namespace="{TARGET_NAMESPACE}", pod=~"{TARGET_DEPLOYMENT}.*"}}[5m]))',
            "queue_length": f'avg(queue_size{{namespace="{TARGET_NAMESPACE}", job="{TARGET_DEPLOYMENT}"}})',
            "response_time": f'avg(http_request_duration_seconds{{namespace="{TARGET_NAMESPACE}", pod=~"{TARGET_DEPLOYMENT}.*"}})',
            "active_connections": f'sum(active_connections{{namespace="{TARGET_NAMESPACE}", pod=~"{TARGET_DEPLOYMENT}.*"}})'
        }
        tasks = [self.query_metric(q) for q in queries.values()]
        results = await asyncio.gather(*tasks)
        return PrometheusMetrics(**dict(zip(queries.keys(), results)))

# initialise singleton Prometheus client
prom_client = PrometheusClient(PROMETHEUS_URL)

# ---------------------------------------------------
# Model / feature helpers
# ---------------------------------------------------

def _load_feature_names_from_metadata(path: str) -> List[str]:
    """Attempt to read feature name order from a metadata json produced during training."""
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r") as f:
            meta = json.load(f)
        return meta.get("selected_features", []) or meta.get("feature_names", [])
    except Exception as ex:
        logger.warning(f"Could not read metadata file {path}: {ex}")
        return []

def load_model_and_features() -> bool:
    """Load the ML model and capture expected feature names."""
    global model, expected_feature_names
    try:
        model = joblib.load(MODEL_PATH)
        logger.info(f"✅ Model loaded from {MODEL_PATH}")

        # 1) Try to read explicit feature list from metadata file
        expected_feature_names = _load_feature_names_from_metadata(MODEL_METADATA_PATH)

        # 2) Fallback to introspection (scikit‑learn 1.0+ models expose n_features_in_)
        if not expected_feature_names:
            num_features = getattr(model, "n_features_in_", None)
            if num_features is not None:
                expected_feature_names = [f"f_{i}" for i in range(num_features)]
                logger.warning("Using synthetic feature names – order may be incorrect.")

        if not expected_feature_names:
            raise ValueError("Could not determine expected feature names for the model – prediction will fail.")

        logger.info(f"Model expects {len(expected_feature_names)} features.")
        return True
    except Exception as ex:
        logger.error(f"❌ Failed to load model: {ex}")
        model = None
        return False


def build_feature_vector(metrics: PrometheusMetrics) -> np.ndarray:
    """Create a numpy feature vector in the exact order the model expects.

    Any engineered features not available at prediction time are filled with 0.
    The six real‑time metrics are mapped when their names are present in the
    expected feature list (e.g. 'cpu_usage').
    """
    global expected_feature_names

    # Map base metrics to names
    base = {
        "cpu_usage": metrics.cpu_usage,
        "memory_usage": metrics.memory_usage,
        "request_rate": metrics.request_rate,
        "queue_length": metrics.queue_length,
        "response_time": metrics.response_time,
        "active_connections": metrics.active_connections,
        # a couple of simple engineered metrics we *can* compute on‑the‑fly
        "cpu_memory_ratio": metrics.cpu_usage / (metrics.memory_usage + 1e-6),
        "network_total": metrics.request_rate  # placeholder – better than 0
    }

    # Build feature vector
    vec = np.zeros(len(expected_feature_names), dtype=float)
    for idx, fname in enumerate(expected_feature_names):
        if fname in base:
            vec[idx] = base[fname]
        # else leave as 0 (unknown engineered feature)
    return vec.reshape(1, -1)

# ---------------------------------------------------
# Lifespan events
# ---------------------------------------------------
@app.on_event("startup")
async def _startup() -> None:
    if not load_model_and_features():
        logger.error("Model or features could not be loaded – /predict endpoints will return 503.")

@app.on_event("startup")
async def _background_prediction_loop() -> None:
    """Continuously call prediction every 30 s so Prometheus/KEDA have fresh data."""
    async def _runner():
        while True:
            try:
                if model is not None:
                    await predict_from_prometheus()
            except Exception as ex:
                logger.error(f"Background prediction error: {ex}")
            await asyncio.sleep(30)

    asyncio.create_task(_runner())

# ---------------------------------------------------
# Utility endpoints
# ---------------------------------------------------
@app.get("/health")
async def health_check():
    """Health check combining model + Prometheus connectivity"""
    prom_ok = False
    try:
        await prom_client.query_metric("up")
        prom_ok = True
    except Exception:
        pass

    return {
        "status": "healthy" if (model and prom_ok) else "unhealthy",
        "model_loaded": model is not None,
        "prometheus_connected": prom_ok,
        "expected_features": len(expected_feature_names),
        "timestamp": datetime.utcnow().isoformat()
    }

# ---------------------------------------------------
# Core prediction endpoints
# ---------------------------------------------------
@app.get("/predict-from-prometheus", response_model=PredictionResponse)
async def predict_from_prometheus():
    if model is None or not expected_feature_names:
        raise HTTPException(status_code=503, detail="Model not loaded or feature names unavailable")

    metrics = await prom_client.get_workload_metrics()
    feature_vector = build_feature_vector(metrics)

    try:
        raw_pred = model.predict(feature_vector)[0]
    except ValueError as ex:
        # Feature mismatch – expose details for easier debugging
        raise HTTPException(status_code=500, detail=f"Prediction failed: {ex}")

    # Confidence – best effort
    confidence = 0.95
    if hasattr(model, 'predict_proba'):
        try:
            confidence = float(np.max(model.predict_proba(feature_vector)))
        except Exception:
            pass

    pods = max(1, int(round(raw_pred)))

    # Update custom Prometheus metrics
    prediction_counter.inc()
    prediction_gauge.set(pods)
    model_confidence_gauge.set(confidence)

    logger.info(f"🔮 Predicted {pods} pods (confidence {confidence:.2f})")

    return PredictionResponse(
        predicted_pod_count=pods,
        confidence=confidence,
        timestamp=datetime.utcnow().isoformat(),
        metrics_used=metrics,
        model_version="1.1.0"
    )

@app.get("/keda-metric", response_model=KEDAMetricResponse)
async def keda_metric():
    try:
        prediction = await predict_from_prometheus()
        return KEDAMetricResponse(metric_value=prediction.predicted_pod_count, timestamp=prediction.timestamp)
    except HTTPException as http_ex:
        logger.error(f"KEDA metric endpoint failed: {http_ex.detail}")
        # Safe fallback: 1 replica
        return KEDAMetricResponse(metric_value=1, timestamp=datetime.utcnow().isoformat())

# ---------------------------------------------------
# Misc endpoints
# ---------------------------------------------------
@app.get("/prometheus-metrics")
async def prometheus_metrics():
    return generate_latest(registry).decode()

@app.get("/current-metrics")
async def current_metrics():
    metrics = await prom_client.get_workload_metrics()
    return {"metrics": metrics.dict(), "timestamp": datetime.utcnow().isoformat()}

@app.get("/")
async def root():
    return {
        "message": "Kubernetes Pod Autoscaling Predictor with Prometheus Integration",
        "version": "1.1.0",
        "prometheus_url": PROMETHEUS_URL,
        "target_namespace": TARGET_NAMESPACE,
        "target_deployment": TARGET_DEPLOYMENT,
        "expected_features": len(expected_feature_names),
        "endpoints": [
            "/health", "/predict-from-prometheus", "/keda-metric", "/current-metrics", "/prometheus-metrics"
        ]
    }

# ---------------------------------------------------
# Uvicorn entrypoint when run as `python main.py`
# ---------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), log_level="info")
