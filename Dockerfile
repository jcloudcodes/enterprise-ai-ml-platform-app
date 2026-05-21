FROM python:3.11-slim

WORKDIR /app

ENV PIP_PROGRESS_BAR=off
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV OPENBLAS_NUM_THREADS=1
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV NUMEXPR_NUM_THREADS=1
ENV TOKENIZERS_PARALLELISM=false
ENV HF_HUB_DISABLE_XET=1
ENV HF_HUB_DISABLE_PROGRESS_BARS=1
ENV DISABLE_TQDM=1
ENV HF_HOME=/opt/huggingface
ARG PREFETCH_MODELS=false

COPY requirements.txt .

RUN pip install --no-cache-dir --progress-bar off \
    --timeout 300 \
    --retries 10 \
    torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir --progress-bar off \
    --timeout 300 \
    --retries 10 \
    -r requirements.txt

RUN if [ "$PREFETCH_MODELS" = "true" ]; then       python -c "from huggingface_hub import snapshot_download; models=['distilbert-base-uncased-finetuned-sst-2-english','sshleifer/distilbart-cnn-12-6']; [snapshot_download(repo_id=model) for model in models]";     else       echo 'Skipping model prefetch during build; models will lazy-load at runtime';     fi

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
