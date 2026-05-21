from pydantic import BaseModel


class PredictionRequest(BaseModel):
    text: str


class SummaryRequest(BaseModel):
    text: str


class QuestionRequest(BaseModel):
    text: str
