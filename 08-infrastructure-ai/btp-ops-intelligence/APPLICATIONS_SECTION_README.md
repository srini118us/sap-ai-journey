# Applications

## Scope

Production-ready SAP BTP applications demonstrating full-stack development patterns with CAP, HANA Cloud, and AI integrations.

## Use Cases

| # | Use Case | What It Demonstrates | Status |
|---|----------|---------------------|--------|
| 1 | [BTP Ops Intelligence](./btp-ops-intelligence/) | Operations dashboard with Joule NLQ | ✅ Complete |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    BTP APPLICATION STACK                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                   PRESENTATION LAYER                     │   │
│   │                                                          │   │
│   │   ┌───────────┐    ┌───────────┐    ┌───────────┐       │   │
│   │   │ Dashboard │    │   Joule   │    │   Fiori   │       │   │
│   │   │   HTML    │    │   Chat    │    │  Elements │       │   │
│   │   └─────┬─────┘    └─────┬─────┘    └─────┬─────┘       │   │
│   │         │                │                │              │   │
│   │         └────────────────┼────────────────┘              │   │
│   │                          │                               │   │
│   └──────────────────────────┼───────────────────────────────┘   │
│                              │                                   │
│   ┌──────────────────────────┼───────────────────────────────┐   │
│   │                          ▼                                │   │
│   │                  APPLICATION LAYER                        │   │
│   │                                                          │   │
│   │   ┌─────────────────────────────────────────────────┐   │   │
│   │   │                 CAP SERVICE                      │   │   │
│   │   │                                                  │   │   │
│   │   │  • OData V4 Endpoints                            │   │   │
│   │   │  • Custom Handlers (JavaScript)                  │   │   │
│   │   │  • Entity Definitions (CDS)                      │   │   │
│   │   │                                                  │   │   │
│   │   └─────────────────────────────────────────────────┘   │   │
│   │                                                          │   │
│   └──────────────────────────┬───────────────────────────────┘   │
│                              │                                   │
│   ┌──────────────────────────┼───────────────────────────────┐   │
│   │                          ▼                                │   │
│   │                  PERSISTENCE LAYER                        │   │
│   │                                                          │   │
│   │   ┌───────────┐    ┌───────────┐    ┌───────────┐       │   │
│   │   │   HANA    │    │  SQLite   │    │  Object   │       │   │
│   │   │   Cloud   │    │  (local)  │    │   Store   │       │   │
│   │   └───────────┘    └───────────┘    └───────────┘       │   │
│   │                                                          │   │
│   └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## BTP Ops Intelligence

Operations dashboard for monitoring BTP landscape health, costs, alerts, and compliance.

### Features

- 9 OData endpoints for different operational domains
- Custom dashboard UI with real-time data
- Joule-style chat widget for natural language queries
- HANA Cloud persistence

### OData Endpoints

| Endpoint | Description |
|----------|-------------|
| `/odata/v4/ops/SystemHealth` | System health status |
| `/odata/v4/ops/CostTrends` | Monthly cost data |
| `/odata/v4/ops/ActiveAlerts` | Current alerts |
| `/odata/v4/ops/UserActivity` | User metrics |
| `/odata/v4/ops/ServiceStatus` | Service availability |
| `/odata/v4/ops/Incidents` | Open incidents |
| `/odata/v4/ops/Deployments` | Recent deployments |
| `/odata/v4/ops/Compliance` | Compliance status |
| `/odata/v4/ops/Capacity` | Resource utilization |

## Structure

```
applications/
├── README.md                    # This file
└── btp-ops-intelligence/
    ├── README.md
    ├── app/
    │   └── dashboard.html       # Custom UI
    ├── db/
    │   └── schema.cds           # Entity definitions
    ├── srv/
    │   ├── ops-service.cds      # Service definition
    │   └── ops-service.js       # Custom handlers
    ├── package.json
    └── mta.yaml                 # Cloud Foundry deployment
```

## Key Technologies

| Technology | Purpose |
|------------|---------|
| SAP CAP | Application framework |
| HANA Cloud | Database |
| Cloud Foundry | Deployment runtime |
| Work Zone | Portal integration |

## Deployment Notes

- HANA Cloud on trial auto-stops after idle period
- Start HANA instance 5-10 minutes before demos
- CF apps may also auto-stop; use `cf start` to restart

## Reference

- [SAP CAP](https://cap.cloud.sap/docs)
- [SAP HANA Cloud](https://help.sap.com/docs/hana-cloud)
- [Cloud Foundry on BTP](https://help.sap.com/docs/btp/sap-business-technology-platform/cloud-foundry-environment)
