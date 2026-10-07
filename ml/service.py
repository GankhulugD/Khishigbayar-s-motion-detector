"""
MotionCare — ML үйлчилгээ (FastAPI)

Next.js сервер ML_SERVICE_URL тохируулсан үед 2 секундийн цонхыг энд POST /predict-ээр илгээнэ.
Сургасан загвар (models/model.pkl) байхгүй бол алдаа буцааж, веб систем өөрийн baseline ангилагч руу шилжинэ.

Ажиллуулах:
    pip install -r requirements.txt
    uvicorn service:app --port 8000
    # Next.js талд: ML_SERVICE_URL=http://localhost:8000
"""
from pathlib import Path

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from features import extract_features

CLASSES = ["sitting", "standing", "walking", "running", "lying", "fall"]
MODEL_PATH = Path(__file__).parent / "models" / "model.pkl"

app = FastAPI(title="MotionCare ML")
model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None


class Sample(BaseModel):
    t: float
    ax: float
    ay: float
    az: float
    gx: float
    gy: float
    gz: float


class Window(BaseModel):
    deviceId: str
    samples: list[Sample]


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL_PATH.name if model else None}


@app.post("/predict")
def predict(w: Window):
    if model is None:
        raise HTTPException(503, "model not trained yet — run train.py")
    x = np.array([[s.ax, s.ay, s.az, s.gx, s.gy, s.gz] for s in w.samples], dtype=np.float32)
    proba = model.predict_proba([extract_features(x)])[0]
    scores = {c: 0.0 for c in CLASSES}
    for cls, p in zip(model.classes_, proba):
        scores[str(cls)] = float(p)
    activity = max(scores, key=scores.get)
    return {"activity": activity, "scores": scores, "model": "random-forest-v1"}
