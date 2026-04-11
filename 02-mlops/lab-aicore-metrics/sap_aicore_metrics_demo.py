"""
SAP AI CORE METRICS API - DEMONSTRATION
========================================
Educational script showing how metrics tracking works in SAP AI Core.

This demonstrates:
1. Metrics logging (accuracy, loss, custom metrics)
2. Step-based tracking (per epoch)
3. Tags and metadata
4. Custom info (JSON reports)

Author: Srinivasa Dasari
Lab: SAP AI Core Metrics

NOTE: Metrics persistence ONLY works inside SAP AI Core execution environment.
      This script shows the code patterns for integration.
"""

from datetime import datetime
from typing import List, Dict, Any
import json

# ==============================================================================
# SECTION 1: MOCK SAP AI CORE SDK CLASSES
# ==============================================================================
# These mirror the actual SAP AI Core SDK classes for local demonstration.
# In production, import from: ai_core_sdk.tracking and ai_core_sdk.models

class Metric:
    """Represents a single metric measurement."""
    def __init__(
        self,
        name: str,
        value: float,
        timestamp: datetime = None,
        step: int = None,
        labels: List[str] = None
    ):
        self.name = name
        self.value = value
        self.timestamp = timestamp or datetime.utcnow()
        self.step = step
        self.labels = labels or []
    
    def __repr__(self):
        return f"Metric(name='{self.name}', value={self.value}, step={self.step})"


class MetricTag:
    """Metadata tag for categorizing metrics."""
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value
    
    def __repr__(self):
        return f"MetricTag(name='{self.name}', value='{self.value}')"


class MetricCustomInfo:
    """Store custom information like JSON reports."""
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value
    
    def __repr__(self):
        return f"MetricCustomInfo(name='{self.name}')"


class Tracking:
    """
    Mock SAP AI Core Tracking client.
    
    In production, this connects to SAP AI Core execution environment
    and persists metrics to AI Launchpad.
    
    Usage:
        from ai_core_sdk.tracking import Tracking
        tracking = Tracking()
    """
    
    def __init__(self):
        self._metrics = []
        self._tags = []
        self._custom_info = []
        self._is_production = False  # Would be True in AI Core
        print("[INIT] SAP AI Core Tracking client initialized")
        print("[INFO] Environment: LOCAL (metrics will not persist)")
        print("[INFO] In AI Core execution: metrics persist to AI Launchpad")
        print()
    
    def log_metrics(self, metrics: List[Metric]):
        """
        Log one or more metrics.
        
        In production (AI Core), these are saved and visible in AI Launchpad.
        Locally, they are stored in memory for demonstration.
        
        Args:
            metrics: List of Metric objects
        """
        for metric in metrics:
            self._metrics.append(metric)
            print(f"[METRIC] {metric.name}: {metric.value}")
            if metric.step is not None:
                print(f"         Step: {metric.step}")
    
    def set_tags(self, tags: List[MetricTag]):
        """
        Set metadata tags for the execution.
        
        Tags help categorize and filter metrics in AI Launchpad.
        
        Args:
            tags: List of MetricTag objects
        """
        for tag in tags:
            self._tags.append(tag)
            print(f"[TAG] {tag.name}: {tag.value}")
    
    def modify(
        self,
        tags: List[MetricTag] = None,
        metrics: List[Metric] = None,
        custom_info: List[MetricCustomInfo] = None
    ):
        """
        Modify/add tags, metrics, and custom info in one call.
        
        This is useful for batch updates.
        """
        if tags:
            self.set_tags(tags)
        if metrics:
            self.log_metrics(metrics)
        if custom_info:
            for info in custom_info:
                self._custom_info.append(info)
                print(f"[CUSTOM INFO] {info.name}: (stored)")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all logged metrics (for demonstration)."""
        return {
            "metrics_count": len(self._metrics),
            "tags_count": len(self._tags),
            "custom_info_count": len(self._custom_info),
            "metrics": [{"name": m.name, "value": m.value, "step": m.step} for m in self._metrics],
            "tags": [{"name": t.name, "value": t.value} for t in self._tags]
        }


# ==============================================================================
# SECTION 2: TRAINING SIMULATION WITH METRICS
# ==============================================================================

def simulate_model_training(tracking: Tracking, epochs: int = 5):
    """
    Simulate model training with metrics logging.
    
    This demonstrates how to integrate metrics into a training loop.
    """
    print("=" * 60)
    print("SIMULATING MODEL TRAINING WITH METRICS")
    print("=" * 60)
    print()
    
    # Set execution tags
    tracking.set_tags(
        tags=[
            MetricTag(name="Model Type", value="XGBoost"),
            MetricTag(name="Dataset", value="Payment Delay"),
            MetricTag(name="Stage", value="Training"),
            MetricTag(name="Environment", value="Development"),
        ]
    )
    print()
    
    # Simulate training epochs
    import random
    random.seed(42)
    
    train_losses = [0.85, 0.62, 0.45, 0.31, 0.22]
    val_losses = [0.88, 0.68, 0.52, 0.42, 0.38]
    accuracies = [0.72, 0.81, 0.87, 0.91, 0.94]
    
    print("-" * 60)
    print("Training Progress:")
    print("-" * 60)
    
    for epoch in range(epochs):
        # Log training metrics per epoch
        tracking.log_metrics(
            metrics=[
                Metric(
                    name="training_loss",
                    value=train_losses[epoch],
                    timestamp=datetime.utcnow(),
                    step=epoch + 1
                ),
                Metric(
                    name="validation_loss",
                    value=val_losses[epoch],
                    timestamp=datetime.utcnow(),
                    step=epoch + 1
                ),
                Metric(
                    name="accuracy",
                    value=accuracies[epoch],
                    timestamp=datetime.utcnow(),
                    step=epoch + 1
                ),
            ]
        )
        print()
    
    # Log final metrics
    print("-" * 60)
    print("Final Metrics:")
    print("-" * 60)
    
    tracking.log_metrics(
        metrics=[
            Metric(name="final_accuracy", value=accuracies[-1]),
            Metric(name="final_loss", value=train_losses[-1]),
            Metric(name="epochs_completed", value=float(epochs)),
        ]
    )
    print()
    
    # Log custom info (classification report as JSON)
    classification_report = {
        "On-Time Payment": {"precision": 0.92, "recall": 0.95, "f1": 0.93},
        "Delayed Payment": {"precision": 0.89, "recall": 0.84, "f1": 0.86},
        "overall_accuracy": 0.94
    }
    
    tracking.modify(
        custom_info=[
            MetricCustomInfo(
                name="Classification Report",
                value=json.dumps(classification_report, indent=2)
            ),
            MetricCustomInfo(
                name="Feature Importance",
                value=json.dumps({
                    "invoice_amount": 0.35,
                    "vendor_risk_score": 0.28,
                    "days_since_payment": 0.22,
                    "payment_terms": 0.15
                })
            )
        ]
    )


# ==============================================================================
# SECTION 3: DRIFT MONITORING METRICS
# ==============================================================================

def log_drift_metrics(tracking: Tracking):
    """
    Demonstrate logging drift-related metrics.
    
    This shows how to implement model monitoring in SAP AI Core
    since there's no built-in drift detection like Vertex AI.
    """
    print()
    print("=" * 60)
    print("LOGGING DRIFT MONITORING METRICS")
    print("=" * 60)
    print()
    
    # Set monitoring tags
    tracking.set_tags(
        tags=[
            MetricTag(name="Stage", value="Monitoring"),
            MetricTag(name="Check Type", value="Drift Detection"),
        ]
    )
    print()
    
    # Simulate drift metrics (would be calculated in real scenario)
    drift_metrics = {
        "invoice_amount_js_divergence": 0.15,
        "vendor_risk_score_js_divergence": 0.08,
        "days_since_payment_js_divergence": 0.22,
        "payment_terms_js_divergence": 0.05,
    }
    
    print("-" * 60)
    print("Feature Drift Metrics:")
    print("-" * 60)
    
    metrics_to_log = []
    for feature, value in drift_metrics.items():
        status = "[DRIFT]" if value > 0.1 else "[OK]"
        metrics_to_log.append(
            Metric(name=feature, value=value, timestamp=datetime.utcnow())
        )
        print(f"  {feature}: {value:.3f} {status}")
    
    tracking.log_metrics(metrics=metrics_to_log)
    print()
    
    # Log overall drift status
    max_drift = max(drift_metrics.values())
    tracking.log_metrics(
        metrics=[
            Metric(name="max_drift_score", value=max_drift),
            Metric(name="drift_threshold", value=0.1),
            Metric(name="drift_detected", value=1.0 if max_drift > 0.1 else 0.0),
        ]
    )


# ==============================================================================
# SECTION 4: PRODUCTION CODE TEMPLATE
# ==============================================================================

def print_production_template():
    """Print the production code template for SAP AI Core."""
    
    print()
    print("=" * 70)
    print("PRODUCTION CODE TEMPLATE FOR SAP AI CORE")
    print("=" * 70)
    print()
    print('''
# =============================================================================
# PRODUCTION CODE: Use this in your SAP AI Core training workflows
# =============================================================================

from datetime import datetime
from ai_core_sdk.tracking import Tracking
from ai_core_sdk.models import Metric, MetricTag, MetricCustomInfo

# Initialize tracking (connects to AI Core execution environment)
tracking = Tracking()

# Set execution metadata
tracking.set_tags(
    tags=[
        MetricTag(name="Model", value="PaymentDelayPredictor"),
        MetricTag(name="Version", value="1.0.0"),
        MetricTag(name="Dataset", value="invoice_data_2024"),
    ]
)

# During training loop
for epoch in range(num_epochs):
    # ... training code ...
    
    tracking.log_metrics(
        metrics=[
            Metric(
                name="training_loss",
                value=float(loss),
                timestamp=datetime.utcnow(),
                step=epoch
            ),
            Metric(
                name="validation_accuracy",
                value=float(val_acc),
                timestamp=datetime.utcnow(),
                step=epoch
            ),
        ]
    )

# After training - log final metrics
tracking.log_metrics(
    metrics=[
        Metric(name="final_accuracy", value=float(final_acc)),
        Metric(name="final_f1_score", value=float(f1)),
        Metric(name="training_duration_seconds", value=float(duration)),
    ]
)

# Store custom reports
tracking.modify(
    custom_info=[
        MetricCustomInfo(
            name="confusion_matrix",
            value=str(confusion_matrix.tolist())
        ),
        MetricCustomInfo(
            name="feature_importance",
            value=json.dumps(importance_dict)
        ),
    ]
)
''')


# ==============================================================================
# SECTION 5: MAIN EXECUTION
# ==============================================================================

def main():
    """Run the SAP AI Core metrics demonstration."""
    
    print()
    print("#" * 70)
    print("#  SAP AI CORE METRICS API - DEMONSTRATION")
    print("#" * 70)
    print()
    
    # Initialize tracking
    tracking = Tracking()
    
    # Simulate training with metrics
    simulate_model_training(tracking, epochs=5)
    
    # Simulate drift monitoring
    log_drift_metrics(tracking)
    
    # Print summary
    print()
    print("=" * 60)
    print("METRICS SUMMARY")
    print("=" * 60)
    summary = tracking.get_summary()
    print(f"  Total Metrics Logged: {summary['metrics_count']}")
    print(f"  Total Tags Set: {summary['tags_count']}")
    print(f"  Custom Info Items: {summary['custom_info_count']}")
    
    # Print production template
    print_production_template()
    
    print()
    print("#" * 70)
    print("#  DEMONSTRATION COMPLETE")
    print("#" * 70)
    print()
    print("Key Points:")
    print("  1. Use Tracking() from ai_core_sdk.tracking")
    print("  2. Log metrics with name, value, timestamp, step")
    print("  3. Use tags for metadata (model type, stage, version)")
    print("  4. Store JSON reports in MetricCustomInfo")
    print("  5. Metrics ONLY persist in AI Core execution environment")
    print("  6. View metrics in SAP AI Launchpad")
    print()


if __name__ == "__main__":
    main()