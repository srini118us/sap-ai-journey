"""
SAP AI Core Metrics - Hello World with Tracking
"""
from datetime import datetime
from ai_core_sdk.tracking import Tracking
from ai_core_sdk.models import Metric, MetricTag, MetricCustomInfo
import json

print("[START] Hello from SAP AI Core with Metrics!")

# Initialize tracking
tracking = Tracking()

# Set execution tags
print("[TAGS] Setting execution metadata...")
tracking.set_tags(
    tags=[
        MetricTag(name="Pipeline", value="HelloMetrics"),
        MetricTag(name="Version", value="1.0.0"),
        MetricTag(name="Author", value="Srinivasa"),
    ]
)

# Simulate training metrics
print("[METRICS] Logging training metrics...")
epochs = 5
for epoch in range(1, epochs + 1):
    loss = 1.0 / epoch  # Decreasing loss
    accuracy = 0.5 + (epoch * 0.1)  # Increasing accuracy
    
    tracking.log_metrics(
        metrics=[
            Metric(name="loss", value=loss, timestamp=datetime.utcnow(), step=epoch),
            Metric(name="accuracy", value=accuracy, timestamp=datetime.utcnow(), step=epoch),
        ]
    )
    print(f"  Epoch {epoch}: loss={loss:.3f}, accuracy={accuracy:.2f}")

# Log final metrics
print("[METRICS] Logging final metrics...")
tracking.log_metrics(
    metrics=[
        Metric(name="final_accuracy", value=0.95, timestamp=datetime.utcnow()),
        Metric(name="final_loss", value=0.05, timestamp=datetime.utcnow()),
        Metric(name="epochs_completed", value=float(epochs), timestamp=datetime.utcnow()),
    ]
)

# Store custom info
print("[CUSTOM] Storing custom info...")
tracking.modify(
    custom_info=[
        MetricCustomInfo(
            name="model_summary",
            value=json.dumps({"type": "demo", "framework": "none", "purpose": "metrics_test"})
        )
    ]
)

print("[DONE] Pipeline completed successfully!")