import os, joblib, pandas as pd
from flask import Flask, request, jsonify

app = Flask(__name__)

MODEL_DIR = "/mnt/models"
model = joblib.load(os.path.join(MODEL_DIR, "model.joblib"))
columns = joblib.load(os.path.join(MODEL_DIR, "columns.joblib"))

@app.route("/v1/predict", methods=["POST"])
def predict():
    payload = request.get_json(force=True)
    rows = payload if isinstance(payload, list) else [payload]
    df = pd.get_dummies(pd.DataFrame(rows))
    df = df.reindex(columns=columns, fill_value=0)
    proba = model.predict_proba(df)[:, 1]
    return jsonify([
        {"delay_probability": float(p), "predicted_delayed": int(p >= 0.5)}
        for p in proba
    ])

@app.route("/v1/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"})