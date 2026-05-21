from fastapi import APIRouter

from app.ai_model import (
    ANSWER_MODEL_NAME,
    SENTIMENT_MODEL_NAME,
    SUMMARY_MODEL_NAME,
    get_answer_model,
    get_model_errors,
    get_model_loading_state,
    get_model_providers,
    get_sentiment_model,
    get_summary_model,
)
from app.metrics import REQUEST_COUNT

router = APIRouter()


@router.get("/health")
async def health():
    sentiment_ready = get_sentiment_model() is not None
    summary_ready = get_summary_model() is not None
    answer_ready = get_answer_model() is not None
    loading_state = get_model_loading_state()
    model_errors = get_model_errors()
    model_providers = get_model_providers()

    if sentiment_ready and summary_ready and answer_ready:
        status = "healthy"
    elif loading_state["sentiment"] or loading_state["summarization"] or loading_state["answer"]:
        status = "loading"
    else:
        status = "ready_for_lazy_load"

    REQUEST_COUNT.labels(
        endpoint="/health",
        method="GET",
        status=status,
    ).inc()

    return {
        "status": status,
        "models": {
            "sentiment": {
                "ready": sentiment_ready,
                "loading": loading_state["sentiment"],
                "model": SENTIMENT_MODEL_NAME,
                "provider": model_providers["sentiment"],
                "error": model_errors["sentiment"],
            },
            "summarization": {
                "ready": summary_ready,
                "loading": loading_state["summarization"],
                "model": SUMMARY_MODEL_NAME,
                "provider": model_providers["summarization"],
                "error": model_errors["summarization"],
            },
            "answer": {
                "ready": answer_ready,
                "loading": loading_state["answer"],
                "model": ANSWER_MODEL_NAME,
                "provider": model_providers["answer"],
                "error": model_errors["answer"],
            },
        },
        "platform": "Enterprise AI/ML Platform",
    }
