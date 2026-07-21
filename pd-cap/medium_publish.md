After You Ship the Agent, the Real Work Begins
Building a governed, self-monitoring multi-agent finance system on Databricks, fed by SAP Business Data Cloud
A few weeks ago I wrote about building a cashflow forecasting agent on SAP BTP: the forecaster, the SHAP explainer, the Joule conversation. That piece ended where most agent articles end, at delivery.

This is what I built next, on a different stack. Building an agent is increasingly accessible. Keeping it governed, trustworthy, and observable after deployment is the harder engineering problem. This build explores what happens after deployment: governance propagation, confidence-aware reasoning, drift detection, and operational trust, keeping lineage and trust intact across the boundary between SAP and Databricks.

The system is three specialist agents, a supervisor that reasons across them, and a trust triad built by hand: data-honesty, drift-monitoring, and output-safety.

A Note on the Environment: This entire architecture was developed and validated end-to-end utilizing the SAP Business Data Cloud Trial and the Databricks Trial environments. Navigating the standard boundaries of these evaluation tiers required building several core orchestration, monitoring, and safety patterns from scratch—proving that enterprise-grade AI governance can be engineered from first principles without relying on gated platform premium upgrades.

Refer to SAPDataBricks_SupervisorAgent.png below to trace the complete pipeline from core SAP data entities to the final autonomous and human-in-the-loop validation layers:

Figure 1: Complete multi-agent pipeline topology bridging SAP BDC Connect, Databricks Unity Catalog, the three-way specialist synthesis layer, and the evaluation harness.

Technologies: SAP Business Data Cloud, SAP Datasphere, SAP BDC Connect, Delta Sharing, Databricks Unity Catalog, Mosaic AI Agent Bricks, Vector Search, MCP, XGBoost, SHAP.

Architecture principles
Four ideas run through every layer of this build, and they are the lens for the rest of the article:

Governance must survive every layer, not just sit at the source.

Confidence is metadata, not a UI feature.

Monitoring is part of the product, not an afterthought.

Human review remains a first-class control, not a fallback.

Part 1: The foundation
The data does not jump straight from S/4HANA into Databricks. It travels a deliberate, governed path:

S/4HANA to Datasphere object store: finance data replicated as Parquet.

Published as a managed data product in SAP Business Data Cloud.

Shared through BDC Connect over the Delta Sharing protocol. This object-store hop matters: Delta Sharing does not work against HANA tables directly.

Mounts into Databricks Unity Catalog, behaving like any other Delta-shared asset.

Medallion refinement to gold, then an XGBoost model with a SHAP explainer (covered in the previous article).

A scheduled Databricks Job retrains the model so it does not go stale.

Unity Catalog governs all of it (shared data, gold tables, model, tools) with access, lineage, and audit in one place.

One honest note, because "zero-copy" gets oversold. The share is zero-copy: the SAP data stays in place and Databricks reads it live. But the gold tables I build are aggregations, materialized derivatives, so there is a deliberate copy at the gold layer. The accurate description is zero-copy access at the boundary, materialized gold inside the lakehouse.

That is the foundation. It is competent, not unique. It establishes data quality, lineage, and governance, but none of it guarantees trustworthy AI behaviour. That begins in the layers above.

Part 2: Making it trustworthy
Four distinct components elevate this layer beyond a simple chatbot over database tables. The architecture diagram above illustrates their placement; this section explains why they are critical to the system's integrity.

One: governance that survives the hierarchy
A vendor with a single on-time purchase order will display a 100% on-time delivery rate. While technically accurate, this metric is completely misleading to a business leader.

To solve this, I built a data-confidence guard directly into the gold data layer. Any vendor with too few historical orders is automatically flagged as "low-confidence" and programmatically excluded from performance rankings.

The same protective guard is applied to the journal-risk data. On thin data sets, an anomaly rate is usually just noise disguised as a signal. Every specialized agent in this framework natively carries this guard.

[Gold Layer Flag] ──> [Specialist Agent] ──> [Supervisor] ──> [User Warning]
The defining engineering goal was ensuring this flag survived the entire multi-agent journey. It originates in the gold layer, climbs through the agent hierarchy, and successfully reaches the end user as a clear caveat:

System Warning: These rates rest on small data samples. Treat them as indicative.

When tested against company codes with high anomaly rates, the agent surfaced the risks but immediately appended the sample size warning. Next to a company code containing 38,584 entries, the system's honesty was enforced end-to-end.

Governance cannot just be a visual UI filter applied at the tail end of a workflow. It must be an unyielding property built into every layer, especially when a supervisor agent could easily smooth the edge cases away.

Two: a supervisor that synthesises, not just routes
This system deploys three distinct specialists across three different operational axes:

Cash-Flow-Analyst: Focuses purely on enterprise liquidity.

Vendor-Performance-Analyst: Tracks delivery risk and operational metrics.

Journal-Risk-Analyst: Evaluates control integrity using an Isolation Forest model to flag unusual postings.

Simply routing a user's question to the correct specialist is straightforward engineering, but it offers limited business value. The true value lies in automated cross-domain synthesis.

For example, when asked for a financial risk overview of a specific company code, the supervisor consulted all three specialists and connected the dots. It recognized a strong cash flow, but flagged two underperforming vendors alongside a journal anomaly pattern where 78% of unusual postings occurred on weekends.

The supervisor highlighted this convergence. Together, the delivery and control signals pointed to an operational risk that the company's strong cash position could absorb—if addressed early.

No individual specialist agent had the context to reach that conclusion independently. This cross-domain reasoning is the real argument for a multi-agent hierarchy.

Three: drift, and the harness that watches for it
An agent system that functions perfectly today is not guaranteed to work correctly next month. Prompts get edited, underlying LLM models get updated by providers, data distributions shift, and routing that was once accurate silently degrades.

To counter this, I hand-built an automated evaluation harness. It stores expected routing behaviors, tool selections, and exact answer characteristics inside a versioned, governed Delta table.

Scheduled jobs automatically run the golden test set against live agent endpoints. The framework compares real-time behavior against historical baselines and appends the metrics over time.

[Golden Test Set] ──> [Live Endpoint Run] ──> [Log to Delta Table] ──> [Drift Trend]
A single run is just a unit test. A growing history of runs forms a true drift-detection record. This baseline is what tells you the system’s accuracy degraded in week six, even though no cloud infrastructure logs threw an error.

However, monitoring introduces a distinct challenge: who judges the judge? Simple substring check scripts are precise but brittle. Evaluating open-ended answer quality requires a secondary LLM judge, which itself can drift over time. Production monitoring remains an evolving design problem.

Four: the guardrail on the way out
The final layer inspects the supervisor's response right before it reaches the user. Because managed platform tools like the Unity AI Gateway were gated on the trial tier, I engineered an equivalent verification layer by hand.

This safety layer handles two distinct responsibilities:

Generic Control: Scans the payload to prevent sensitive data or PII leaks.

Business Logic Control: Enforces the system's honesty contract (e.g., a journal anomaly must never be stated as a "confirmed fraud").

This layer also serves as an automated operational fork. High-confidence outputs pass through to the user immediately, while responses carrying low-confidence or highly flagged metadata are routed into a human review queue.

Building this taught me a lesson in edge cases. The first iteration blocked a perfectly valid financial response because the phrase "not confirmed fraud" triggered a match on the blocked substring "confirmed fraud".

The logic had to be rewritten to handle semantic negation. A guardrail that creates constant false positives becomes an operational bottleneck; the guard needs guarding too.

Together, these components form our trust triad: data-honesty at the data tier, drift-monitoring across the lifecycle, and output-safety at the edge.

What I took away
The data-confidence guard was the highest-leverage design decision in the entire system. A simple rule, embedded at the root data layer and propagated upward, did more for system trust than endless hours of prompt tuning.

Furthermore, building the monitoring telemetry was harder than writing the agent instructions—and significantly more valuable. Teams shipping real enterprise systems treat data governance and ongoing observability as the primary engineering work, not an afterthought.

Deploying an LLM agent is easier than ever. The true challenge is keeping it trustworthy and observable over time: ensuring it stays honest when data is thin, reasons across silos, and continues to perform next month.

Building these patterns by hand due to trial tier constraints forced me to move past simple platform configuration. It forced me to actually architect a resilient system.