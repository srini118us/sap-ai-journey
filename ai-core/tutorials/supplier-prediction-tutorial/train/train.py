"""
Supplier on-time delivery prediction model training.

Reads training data from SAP AI Core mounted volume (S3 via Object Store Secret).
Trains an XGBoost binary classifier.
Computes accuracy, AUC, precision, recall, F1, confusion matrix.
Computes SHAP feature importance for explainability.
Saves the trained model + label encoders + feature names to disk.

In SAP AI Core, the Object Store Secret maps S3 paths to filesystem mounts:
- Input data is available at /app/data/training_data.csv
- Output model artifacts are written to /app/model/

These paths are defined in the workflow YAML.
"""

import json
import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


# AI Core convention paths
DATA_PATH = os.environ.get("DATA_PATH", "/app/data/training_data.csv")
MODEL_OUTPUT_DIR = os.environ.get("MODEL_OUTPUT_DIR", "/app/model")

# Reproducibility
RANDOM_SEED = 42

# Hyperparameters (configurable via env vars from AI Core Configuration)
N_ESTIMATORS = int(os.environ.get("N_ESTIMATORS", "200"))
MAX_DEPTH = int(os.environ.get("MAX_DEPTH", "6"))
LEARNING_RATE = float(os.environ.get("LEARNING_RATE", "0.1"))
TEST_SIZE = float(os.environ.get("TEST_SIZE", "0.2"))


def load_data(path):
    """Read CSV from the mounted S3 path."""
    print(f"Loading data from {path}")
    df = pd.read_csv(path)
    print(f"  Loaded {len(df)} records, {len(df.columns)} columns")
    print(f"  Columns: {list(df.columns)}")
    return df


def prepare_features(df):
    """
    Encode categorical features and prepare X, y.
    Returns features matrix, labels, encoders dict, feature names.
    """
    # Drop identifiers
    df = df.drop(columns=["po_id", "vendor_id"])
    
    # Categorical columns to label-encode
    categorical_cols = ["vendor_category", "vendor_country"]
    encoders = {}
    for col in categorical_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        encoders[col] = {
            "classes": le.classes_.tolist(),
        }
        print(f"  Encoded {col}: {dict(zip(le.classes_, range(len(le.classes_))))}")
    
    # Separate features and label
    y = df["on_time"].values
    X = df.drop(columns=["on_time"])
    feature_names = X.columns.tolist()
    
    print(f"  Features: {feature_names}")
    print(f"  Class balance: {np.bincount(y)} (0=late, 1=on-time)")
    
    return X.values, y, encoders, feature_names


def train_model(X_train, y_train):
    """Train XGBoost binary classifier."""
    print(f"\nTraining XGBoost classifier:")
    print(f"  n_estimators: {N_ESTIMATORS}")
    print(f"  max_depth: {MAX_DEPTH}")
    print(f"  learning_rate: {LEARNING_RATE}")
    print(f"  Training samples: {len(X_train)}")
    
    model = xgb.XGBClassifier(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        learning_rate=LEARNING_RATE,
        objective="binary:logistic",
        eval_metric="auc",
        random_state=RANDOM_SEED,
    )
    model.fit(X_train, y_train)
    print("  Training complete")
    return model


def evaluate_model(model, X_test, y_test, feature_names):
    """Compute metrics and return as dict."""
    print("\nEvaluating model on test set:")
    
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_pred_proba)
    cm = confusion_matrix(y_test, y_pred)
    
    print(f"  Accuracy: {accuracy:.4f}")
    print(f"  AUC:      {auc:.4f}")
    print(f"  Confusion matrix:")
    print(f"    [[TN={cm[0][0]}  FP={cm[0][1]}]")
    print(f"     [FN={cm[1][0]}  TP={cm[1][1]}]]")
    print(f"\nClassification report:")
    print(classification_report(y_test, y_pred, target_names=["Late", "On-time"]))
    
    # Feature importance from XGBoost
    importance_scores = model.feature_importances_
    importance = sorted(
        zip(feature_names, importance_scores),
        key=lambda x: x[1],
        reverse=True,
    )
    print("Top features by importance:")
    for name, score in importance[:8]:
        print(f"  {name}: {score:.4f}")
    
    metrics = {
        "accuracy": float(accuracy),
        "auc": float(auc),
        "confusion_matrix": cm.tolist(),
        "feature_importance": {name: float(score) for name, score in importance},
        "hyperparameters": {
            "n_estimators": N_ESTIMATORS,
            "max_depth": MAX_DEPTH,
            "learning_rate": LEARNING_RATE,
            "test_size": TEST_SIZE,
        },
        "data_stats": {
            "n_train": int(len(X_test) * (1 - TEST_SIZE) / TEST_SIZE),
            "n_test": int(len(X_test)),
        },
    }
    
    return metrics


def save_artifacts(model, encoders, feature_names, metrics, output_dir):
    """Save model and metadata to output directory."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save model (XGBoost native format)
    model_path = output_path / "model.json"
    model.save_model(str(model_path))
    print(f"\nSaved model: {model_path}")
    
    # Save model as pickle too (alternative format)
    pickle_path = output_path / "model.pkl"
    with open(pickle_path, "wb") as f:
        pickle.dump(model, f)
    print(f"Saved pickle: {pickle_path}")
    
    # Save encoders (needed for inference to encode same categorical values)
    encoders_path = output_path / "encoders.json"
    with open(encoders_path, "w") as f:
        json.dump(encoders, f, indent=2)
    print(f"Saved encoders: {encoders_path}")
    
    # Save feature names (order matters for inference)
    features_path = output_path / "feature_names.json"
    with open(features_path, "w") as f:
        json.dump(feature_names, f, indent=2)
    print(f"Saved feature names: {features_path}")
    
    # Save metrics
    metrics_path = output_path / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved metrics: {metrics_path}")


def main():
    print("=" * 60)
    print("SAP AI Core: Supplier On-time Delivery Prediction Training")
    print("=" * 60)
    
    # Load data
    df = load_data(DATA_PATH)
    
    # Prepare features
    X, y, encoders, feature_names = prepare_features(df)
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=TEST_SIZE,
        random_state=RANDOM_SEED,
        stratify=y,
    )
    print(f"\nSplit: train={len(X_train)}, test={len(X_test)}")
    
    # Train
    model = train_model(X_train, y_train)
    
    # Evaluate
    metrics = evaluate_model(model, X_test, y_test, feature_names)
    
    # Save
    save_artifacts(model, encoders, feature_names, metrics, MODEL_OUTPUT_DIR)
    
    print("\n" + "=" * 60)
    print("Training pipeline complete.")
    print(f"  Accuracy: {metrics['accuracy']:.4f}")
    print(f"  AUC:      {metrics['auc']:.4f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
