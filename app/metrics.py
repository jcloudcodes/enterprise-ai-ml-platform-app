from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "ai_inference_requests_total",
    "Total AI inference requests",
    ["endpoint", "method", "status"]
)

PREDICTION_COUNT = Counter(
    "ai_predictions_total",
    "Total AI predictions",
    ["label"]
)

PREDICTION_LATENCY = Histogram(
    "ai_prediction_latency_seconds",
    "AI prediction latency"
)
