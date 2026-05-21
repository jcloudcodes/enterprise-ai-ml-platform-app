import logging
import time

from fastapi import APIRouter

from app.ai_model import (
    ANSWER_MODEL_NAME,
    SENTIMENT_MODEL_NAME,
    SUMMARY_MODEL_NAME,
    get_answer_model,
    get_sentiment_model,
    get_model_providers,
    get_summary_model,
    load_answer_model,
    load_sentiment_model,
    load_summary_model,
)
from app.metrics import PREDICTION_COUNT, PREDICTION_LATENCY, REQUEST_COUNT
from app.models import PredictionRequest, QuestionRequest, SummaryRequest

router = APIRouter(prefix="/predict", tags=["AI Inference"])
logger = logging.getLogger("ai_inference.predict")


def _preview_text(text: str, limit: int = 120) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit] + "..."


@router.post("/sentiment")
async def predict_sentiment(request: PredictionRequest):
    start_time = time.time()

    try:
        logger.info("POST /predict/sentiment text=%r", _preview_text(request.text))
        model = get_sentiment_model() or load_sentiment_model()
        result = model(request.text)[0]
        providers = get_model_providers()

        label = result["label"]
        confidence = round(result["score"], 4)

        PREDICTION_COUNT.labels(label=label).inc()

        REQUEST_COUNT.labels(
            endpoint="/predict/sentiment",
            method="POST",
            status="success",
        ).inc()

        PREDICTION_LATENCY.observe(time.time() - start_time)

        logger.info(
            "POST /predict/sentiment result prediction=%s confidence=%.4f provider=%s",
            label,
            confidence,
            providers["sentiment"],
        )

        return {
            "task": "sentiment-analysis",
            "input": request.text,
            "prediction": label,
            "confidence": confidence,
            "model": SENTIMENT_MODEL_NAME,
            "provider": providers["sentiment"],
            "platform": "Enterprise AI/ML Platform",
        }

    except Exception as e:
        REQUEST_COUNT.labels(
            endpoint="/predict/sentiment",
            method="POST",
            status="error",
        ).inc()
        logger.exception("POST /predict/sentiment failed")

        return {"error": str(e)}


@router.post("/summarize")
async def summarize_text(request: SummaryRequest):
    start_time = time.time()

    try:
        logger.info("POST /predict/summarize text=%r", _preview_text(request.text))
        model = get_summary_model() or load_summary_model()
        result = model(
            request.text,
            max_length=80,
            min_length=20,
            do_sample=False,
        )[0]
        providers = get_model_providers()

        REQUEST_COUNT.labels(
            endpoint="/predict/summarize",
            method="POST",
            status="success",
        ).inc()

        PREDICTION_LATENCY.observe(time.time() - start_time)

        logger.info(
            "POST /predict/summarize result summary=%r provider=%s",
            _preview_text(result["summary_text"]),
            providers["summarization"],
        )

        return {
            "task": "summarization",
            "input": request.text,
            "summary": result["summary_text"],
            "model": SUMMARY_MODEL_NAME,
            "provider": providers["summarization"],
            "platform": "Enterprise AI/ML Platform",
        }

    except Exception as e:
        REQUEST_COUNT.labels(
            endpoint="/predict/summarize",
            method="POST",
            status="error",
        ).inc()
        logger.exception("POST /predict/summarize failed")

        return {"error": str(e)}


@router.post("/answer")
async def answer_question(request: QuestionRequest):
    start_time = time.time()

    try:
        logger.info("POST /predict/answer text=%r", _preview_text(request.text))
        model = get_answer_model() or load_answer_model()
        result = model(request.text)
        providers = get_model_providers()

        REQUEST_COUNT.labels(
            endpoint="/predict/answer",
            method="POST",
            status="success",
        ).inc()

        PREDICTION_LATENCY.observe(time.time() - start_time)

        logger.info(
            "POST /predict/answer result answer=%r provider=%s",
            _preview_text(result["answer"]),
            providers["answer"],
        )

        return {
            "task": "question-answering",
            "input": request.text,
            "answer": result["answer"],
            "model": ANSWER_MODEL_NAME,
            "provider": providers["answer"],
            "platform": "Enterprise AI/ML Platform",
            "warning": result.get("warning"),
        }

    except Exception as e:
        REQUEST_COUNT.labels(
            endpoint="/predict/answer",
            method="POST",
            status="error",
        ).inc()
        logger.exception("POST /predict/answer failed")

        return {"error": str(e)}
