from fastapi import FastAPI

from app.routes.health import router as health_router
from app.routes.metrics import router as metrics_router
from app.routes.predict import router as predict_router
from app.routes.ui import router as ui_router

app = FastAPI(title="Enterprise AI/ML Inference API")


app.include_router(ui_router)
app.include_router(health_router)
app.include_router(predict_router)
app.include_router(metrics_router)
