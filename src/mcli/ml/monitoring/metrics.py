"""Prometheus metrics for monitoring"""

from prometheus_client import Counter, Gauge, Histogram, generate_latest

# API metrics
api_requests_total = Counter(
    "api_requests_total", "Total API requests", ["method", "endpoint", "status"]
)

api_request_duration = Histogram(
    "api_request_duration_seconds", "API request duration", ["method", "endpoint"]
)

# Model metrics
model_predictions_total = Counter(
    "model_predictions_total", "Total model predictions", ["model_id", "model_name"]
)

model_prediction_latency = Histogram(
    "model_prediction_latency_seconds", "Model prediction latency", ["model_id"]
)

model_accuracy = Gauge("model_accuracy", "Model accuracy", ["model_id", "dataset"])

# System metrics
active_users = Gauge("active_users", "Number of active users")
active_models = Gauge("active_models", "Number of active models")
cache_hit_rate = Gauge("cache_hit_rate", "Cache hit rate")


def get_metrics():
    """Get Prometheus metrics in text format"""
    return generate_latest().decode("utf-8")
