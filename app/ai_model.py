import os
import re
from typing import Any

SENTIMENT_MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"
SUMMARY_MODEL_NAME = "sshleifer/distilbart-cnn-12-6"
OPENAI_ANSWER_MODEL_NAME = os.getenv("OPENAI_ANSWER_MODEL", "gpt-5-mini")
ANSWER_MODEL_NAME = os.getenv("ANSWER_MODEL_NAME", "enterprise-local-knowledge-assistant")

USE_HF_MODELS = os.getenv("ENABLE_HF_MODELS", "false").lower() == "true"
USE_OPENAI_ANSWER = os.getenv("ENABLE_OPENAI_ANSWER", "true").lower() == "true"
ENABLE_OPENAI_WEB_SEARCH = os.getenv("ENABLE_OPENAI_WEB_SEARCH", "true").lower() == "true"
if USE_OPENAI_ANSWER and os.getenv("OPENAI_API_KEY"):
    ANSWER_MODEL_NAME = OPENAI_ANSWER_MODEL_NAME

sentiment_model = None
summary_model = None
answer_model = None
sentiment_loading = False
summary_loading = False
answer_loading = False
model_errors = {
    "sentiment": None,
    "summarization": None,
    "answer": None,
}
model_providers = {
    "sentiment": "local-fallback",
    "summarization": "local-fallback",
    "answer": "local-knowledge",
}


class SimpleSentimentModel:
    positive_words = {
        "amazing",
        "awesome",
        "best",
        "excellent",
        "fantastic",
        "good",
        "great",
        "happy",
        "impressive",
        "love",
        "nice",
        "perfect",
        "solid",
        "success",
        "wonderful",
    }
    negative_words = {
        "awful",
        "bad",
        "broken",
        "crash",
        "error",
        "fail",
        "failing",
        "failure",
        "hate",
        "horrible",
        "issue",
        "poor",
        "sad",
        "slow",
        "terrible",
    }

    def __call__(self, text: str) -> list[dict[str, Any]]:
        tokens = re.findall(r"[A-Za-z']+", text.lower())
        positive_hits = sum(token in self.positive_words for token in tokens)
        negative_hits = sum(token in self.negative_words for token in tokens)
        total_hits = positive_hits + negative_hits

        if positive_hits >= negative_hits:
            label = "POSITIVE"
            confidence = 0.6 if total_hits == 0 else min(0.99, 0.55 + positive_hits / max(total_hits, 1) * 0.35)
        else:
            label = "NEGATIVE"
            confidence = min(0.99, 0.55 + negative_hits / total_hits * 0.35)

        return [{"label": label, "score": round(confidence, 4)}]


class SimpleSummaryModel:
    def __call__(
        self,
        text: str,
        max_length: int = 80,
        min_length: int = 20,
        do_sample: bool = False,
    ) -> list[dict[str, str]]:
        del do_sample

        cleaned = " ".join(text.split())
        if not cleaned:
            return [{"summary_text": ""}]

        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        summary = " ".join(sentences[:2]).strip()
        if not summary:
            summary = cleaned

        words = summary.split()
        if len(words) > max_length:
            summary = " ".join(words[:max_length]).rstrip(" ,;:") + "..."
        elif len(words) < min_length and len(cleaned.split()) > len(words):
            summary = cleaned

        return [{"summary_text": summary}]


class SimpleAnswerModel:
    knowledge = {
        "what is a noun": "A noun is a word that names a person, place, thing, or idea. Examples include teacher, Lagos, computer, and freedom.",
        "what is noun": "A noun is a word that names a person, place, thing, or idea. Examples include teacher, Lagos, computer, and freedom.",
        "what are mammals": "Mammals are warm-blooded animals with backbones that usually have hair or fur and feed their young with milk. Examples include humans, dogs, whales, and elephants.",
        "what is a mammal": "A mammal is a warm-blooded animal with a backbone that usually has hair or fur and feeds its young with milk.",
        "what is spring boot": "Spring Boot is a Java framework that helps you build production-ready applications quickly with embedded servers, auto-configuration, and opinionated defaults.",
        "what is fastapi": "FastAPI is a modern Python web framework for building APIs quickly with automatic validation, async support, and interactive Swagger documentation.",
        "what is kubernetes": "Kubernetes is a container orchestration platform used to deploy, scale, and manage applications across clusters of machines.",
        "what is helm": "Helm is a package manager for Kubernetes. It helps you define, install, and upgrade Kubernetes applications using charts.",
        "what is argocd": "Argo CD is a GitOps continuous delivery tool for Kubernetes. It watches Git repositories and keeps cluster state aligned with declared manifests.",
        "what is mongodb": "MongoDB is a NoSQL document database that stores data in flexible JSON-like documents instead of relational tables.",
        "what is sentiment analysis": "Sentiment analysis is an NLP task that estimates whether text expresses positive, negative, or neutral emotion or opinion.",
        "what is summarization": "Summarization is the process of condensing a long piece of text into a shorter version while keeping the main meaning.",
    }

    def __call__(self, text: str) -> dict[str, str]:
        normalized = " ".join((text or "").strip().lower().split())

        if normalized in self.knowledge:
            return {
                "answer": self.knowledge[normalized],
                "source": "local-knowledge",
            }

        if "current president" in normalized or "president of america" in normalized or "president of the united states" in normalized:
            return {
                "answer": (
                    "I can answer basic built-in knowledge locally, but I cannot verify live political facts in local mode. "
                    "For current questions like the president of America, connect this endpoint to a live web-search or LLM provider."
                ),
                "source": "local-knowledge",
            }

        if normalized.startswith(("what is", "what are", "who is", "how do", "why is")):
            topic = normalized.rstrip("?.!").replace("what is", "").replace("what are", "").replace("who is", "").replace("how do", "").replace("why is", "").strip()
            return {
                "answer": (
                    "I do not have a live web connection in local mode, but I can help with basic enterprise and technical questions. "
                    + ("Your topic appears to be: " + topic + ". " if topic else "")
                    + "For richer answers, connect this Ask AI endpoint to an external LLM or search provider."
                ),
                "source": "local-knowledge",
            }

        return {
            "answer": (
                "I can currently help with built-in knowledge, summarization, and sentiment analysis. "
                "Ask a direct question like 'What is a noun?', 'What are mammals?', or connect this service to a live model for broader Q&A."
            ),
            "source": "local-knowledge",
        }


class OpenAIAnswerModel:
    def __init__(self):
        from openai import OpenAI

        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = OPENAI_ANSWER_MODEL_NAME
        self.fallback = SimpleAnswerModel()

    def __call__(self, text: str) -> dict[str, str]:
        tools: list[dict[str, str]] = []
        if ENABLE_OPENAI_WEB_SEARCH:
            tools.append({"type": "web_search"})

        try:
            response = self.client.responses.create(
                model=self.model,
                input=text,
                tools=tools,
                instructions=(
                    "You are an enterprise AI assistant embedded inside a Spring Boot application. "
                    "Answer clearly and briefly. If the question asks for current information, use web search when available."
                ),
            )

            answer = getattr(response, "output_text", None)
            if not answer:
                answer = "I could not generate an answer from the external model."

            return {
                "answer": answer,
                "source": "openai-web" if ENABLE_OPENAI_WEB_SEARCH else "openai",
            }
        except Exception as exc:
            fallback_result = self.fallback(text)
            fallback_result["warning"] = (
                "External AI provider unavailable, so a local fallback answer was used: "
                + str(exc)
            )
            return fallback_result


def _try_load_hf_pipeline(task: str, model_name: str):
    from transformers import pipeline

    return pipeline(task, model=model_name, device=-1)


def load_sentiment_model():
    global sentiment_model, sentiment_loading

    if sentiment_model is not None or sentiment_loading:
        return sentiment_model

    sentiment_loading = True

    try:
        if USE_HF_MODELS:
            sentiment_model = _try_load_hf_pipeline("sentiment-analysis", SENTIMENT_MODEL_NAME)
            model_providers["sentiment"] = "huggingface"
            model_errors["sentiment"] = None
        else:
            sentiment_model = SimpleSentimentModel()
            model_providers["sentiment"] = "local-fallback"
            model_errors["sentiment"] = None
    except Exception as exc:
        sentiment_model = SimpleSentimentModel()
        model_providers["sentiment"] = "local-fallback"
        model_errors["sentiment"] = f"Fell back to local model: {exc}"
    finally:
        sentiment_loading = False

    return sentiment_model


def load_summary_model():
    global summary_model, summary_loading

    if summary_model is not None or summary_loading:
        return summary_model

    summary_loading = True

    try:
        if USE_HF_MODELS:
            summary_model = _try_load_hf_pipeline("summarization", SUMMARY_MODEL_NAME)
            model_providers["summarization"] = "huggingface"
            model_errors["summarization"] = None
        else:
            summary_model = SimpleSummaryModel()
            model_providers["summarization"] = "local-fallback"
            model_errors["summarization"] = None
    except Exception as exc:
        summary_model = SimpleSummaryModel()
        model_providers["summarization"] = "local-fallback"
        model_errors["summarization"] = f"Fell back to local model: {exc}"
    finally:
        summary_loading = False

    return summary_model


def load_answer_model():
    global answer_model, answer_loading

    if answer_model is not None or answer_loading:
        return answer_model

    answer_loading = True

    try:
        if USE_OPENAI_ANSWER and os.getenv("OPENAI_API_KEY"):
            answer_model = OpenAIAnswerModel()
            model_providers["answer"] = "openai-web" if ENABLE_OPENAI_WEB_SEARCH else "openai"
            model_errors["answer"] = None
        else:
            answer_model = SimpleAnswerModel()
            model_providers["answer"] = "local-knowledge"
            model_errors["answer"] = None
    except Exception as exc:
        answer_model = SimpleAnswerModel()
        model_providers["answer"] = "local-knowledge"
        model_errors["answer"] = f"Fell back to local knowledge model: {exc}"
    finally:
        answer_loading = False

    return answer_model


def get_sentiment_model():
    return sentiment_model


def get_summary_model():
    return summary_model


def get_answer_model():
    return answer_model


def get_model_errors():
    return model_errors


def get_model_loading_state():
    return {
        "sentiment": sentiment_loading,
        "summarization": summary_loading,
        "answer": answer_loading,
    }


def get_model_providers():
    return model_providers
