# Foundations

## Scope

This section covers the fundamental building blocks of SAP AI Core. Before building production ML applications, understanding these core concepts is essential. The use cases progress from simple to complex, each introducing new capabilities.

## Why "Foundations"

These are not business applications - they are learning exercises that teach how SAP AI Core works under the hood. Master these concepts before moving to other sections.

## Use Cases

| # | Use Case | What It Teaches | Key Technology |
|---|----------|-----------------|----------------|
| 1 | [Hello World](./hello-world/) | Basic workflow execution | Argo WorkflowTemplate |
| 2 | [Hello Metrics](./hello-metrics/) | Custom metrics logging | Argo + AI Core Metrics API |
| 3 | [Model Serving](./model-serving/) | Deploy model as REST API | KServe, ServingTemplate |
| 4 | [Multi-Step Pipeline](./multi-step-pipeline/) | S3 artifacts, data processing | Artifacts, Object Store |

## Learning Path

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Hello World                                                  │
│     └── Understand: Workflows, Scenarios, Executables           │
│              ↓                                                   │
│  2. Hello Metrics                                                │
│     └── Understand: Custom metrics, AI Core tracking API        │
│              ↓                                                   │
│  3. Model Serving                                                │
│     └── Understand: ServingTemplate, KServe, Deployments        │
│              ↓                                                   │
│  4. Multi-Step Pipeline                                          │
│     └── Understand: Artifacts, S3, Multi-step execution         │
└─────────────────────────────────────────────────────────────────┘
```

## Key Concepts Introduced

| Concept | Introduced In | Description |
|---------|---------------|-------------|
| WorkflowTemplate | Hello World | Defines batch/training jobs |
| Scenarios | Hello World | Logical grouping of ML operations |
| Executables | Hello World | Runnable units within scenarios |
| Configurations | Hello World | Parameter sets for executables |
| Executions | Hello World | Actual runs of configurations |
| Metrics API | Hello Metrics | Custom metric logging to AI Core |
| ServingTemplate | Model Serving | Defines inference endpoints |
| KServe | Model Serving | Kubernetes model serving framework |
| Deployments | Model Serving | Running inference services |
| Artifacts | Multi-Step | Files stored in S3 |
| Object Store | Multi-Step | S3 bucket for data storage |

## Prerequisites

- SAP AI Core instance provisioned in BTP
- SAP AI Launchpad subscription
- Git repository connected to AI Core
- Docker Hub account (for model-serving)
- S3 bucket configured (for multi-step-pipeline)

## Structure

```
foundations/
├── README.md                    # This file
├── hello-world/
│   ├── README.md
│   └── workflows/
│       └── hello-world.yaml
├── hello-metrics/
│   ├── README.md
│   └── workflows/
│       └── hello-metrics.yaml
├── model-serving/
│   ├── README.md
│   ├── serve/
│   │   ├── inference.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── workflows/
│       └── serving-template-v3.yaml
└── multi-step-pipeline/
    ├── README.md
    └── workflows/
        └── data-pipeline.yaml
```

## Reference

- [SAP AI Core Documentation](https://help.sap.com/docs/ai-core)
- [SAP AI Core Tutorials](https://developers.sap.com/tutorial-navigator.html?tag=software-product%3Atechnology-platform%2Fsap-ai-core)
