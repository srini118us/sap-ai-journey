namespace btp.intelligent.ops;

// ─────────────────────────────────────────────
// TILE 1: Trust & Connectivity
// SSL Certificates, Cloud Connector, Destinations
// ─────────────────────────────────────────────
entity CertificatesHealth {
    key ID              : UUID;
    region              : String(10);   // US10, EU10, AP10
    subaccount          : String(60);
    certName            : String(80);
    certType            : String(40);   // SSL, OAuth, S4HANA-Tunnel, Integration-Suite
    issuedBy            : String(80);
    expiryDate          : Date;
    daysToExpiry        : Integer;
    status              : String(20);   // Healthy, Warning, Critical, Expired
    associatedService   : String(80);
    autoRenewEnabled    : Boolean;
    lastChecked         : DateTime;
}

entity DestinationsHealth {
    key ID              : UUID;
    region              : String(10);
    subaccount          : String(60);
    destinationName     : String(80);
    destinationType     : String(40);   // HTTP, RFC, LDAP, SuccessFactors
    targetHost          : String(120);
    authType            : String(40);   // BasicAuth, OAuth2, SAMLAssertion, NoAuth
    status              : String(20);   // Reachable, Unreachable, Degraded, Unknown
    responseTimeMs      : Integer;
    lastPingTimestamp   : DateTime;
    failureCount24h     : Integer;
    criticalForProcess  : String(80);
}

// ─────────────────────────────────────────────
// TILE 2: Cloud Economics
// CPEA Credits, Service Spend, Idle Resources
// ─────────────────────────────────────────────
entity CostConsumption {
    key ID              : UUID;
    region              : String(10);
    subaccount          : String(60);
    serviceName         : String(80);
    serviceCategory     : String(40);   // Integration, Data, AI, Runtime, Dev, Analytics
    billingModel        : String(30);   // CPEA, PayPerUse, Subscription, Free
    monthYear           : String(8);    // YYYY-MM
    allocatedBudgetUSD  : Decimal(12,2);
    actualSpendUSD      : Decimal(12,2);
    forecastedSpendUSD  : Decimal(12,2);
    spendVariancePct    : Decimal(5,2);
    creditUnitsUsed     : Decimal(10,2);
    isIdle              : Boolean;
    idleDays            : Integer;
    recommendation      : String(200);
}

// ─────────────────────────────────────────────
// TILE 3: Compute Efficiency
// Datasphere ECNs, HANA Cloud, CF Runtimes
// ─────────────────────────────────────────────
entity ComputeResources {
    key ID              : UUID;
    region              : String(10);
    subaccount          : String(60);
    resourceName        : String(80);
    resourceType        : String(40);   // Datasphere-Space, HANA-Cloud, CF-Space, EventMesh-Queue
    allocatedGB         : Decimal(10,2);
    usedGB              : Decimal(10,2);
    usagePercent        : Decimal(5,2);
    peakUsagePct        : Decimal(5,2);
    lastActivityDate    : Date;
    daysSinceActivity   : Integer;
    isGhostSpace        : Boolean;      // Zero activity > 14 days
    monthlyCostUSD      : Decimal(10,2);
    status              : String(20);   // Optimal, Underutilized, AtRisk, Critical
    scalingRecommend    : String(200);
}

// ─────────────────────────────────────────────
// TILE 4: Innovation & AI ROI
// AI Core, Joule, GenAI Hub consumption
// ─────────────────────────────────────────────
entity AIActivityLog {
    key ID              : UUID;
    region              : String(10);
    subaccount          : String(60);
    agentOrModel        : String(80);   // Joule, gpt-4o, claude-3-sonnet, etc.
    activityType        : String(40);   // Health-Check, Cost-Analysis, Alert-Triage, Recommendation
    aiUnitsConsumed     : Decimal(10,4);
    tokensIn            : Integer;
    tokensOut           : Integer;
    costPerUnitUSD      : Decimal(8,6);
    totalCostUSD        : Decimal(10,4);
    intentSuccessRate   : Decimal(5,2);
    manualHoursReplaced : Decimal(6,2);
    sessionDate         : Date;
    monthYear           : String(8);
}

// ─────────────────────────────────────────────
// CROSS-CUTTING: Operational Alerts & AI Insights
// Powers the "Why + What Next" actionability layer
// ─────────────────────────────────────────────
entity OperationalAlerts {
    key ID              : UUID;
    region              : String(10);
    subaccount          : String(60);
    alertTime           : DateTime;
    severity            : String(10);   // Critical, High, Medium, Low, Info
    alertCategory       : String(30);   // Cost, Health, Security, Capacity, Integration, AI
    title               : String(120);
    description         : String(500);
    affectedService     : String(80);
    isAutoTriaged       : Boolean;
    triageAgent         : String(60);
    status              : String(20);   // Open, In-Progress, Resolved, Suppressed
    resolutionNotes     : String(300);
}

entity AIRecommendations {
    key ID              : UUID;
    region              : String(10);
    generatedAt         : DateTime;
    category            : String(30);   // Cost-Optimize, Scale-Down, Renew-Cert, Fix-Dest, Capacity
    priority            : String(10);   // P1, P2, P3
    what                : String(200);  // What is happening
    why                 : String(300);  // Why it matters
    action              : String(300);  // What to do next
    estimatedSavingUSD  : Decimal(10,2);
    estimatedEffortHrs  : Decimal(5,1);
    affectedService     : String(80);
    status              : String(20);   // New, Accepted, Rejected, Implemented
    acceptedBy          : String(60);
}

// ─────────────────────────────────────────────
// RESTORED FROM RENTED SYSTEM: BTPServices
// Quick service health overview — all services at a glance
// Powers the "Services at Risk" KPI on dashboard
// ─────────────────────────────────────────────
entity BTPServices {
    key ID                  : UUID;
    region                  : String(10);
    subaccount              : String(60);
    serviceName             : String(80);
    serviceType             : String(40);   // Integration, Data, AI, Runtime, Analytics, Dev
    status                  : String(20);   // Active, Warning, Critical, Inactive, Expired
    entitledQuota           : Decimal(12,2);
    currentUsage            : Decimal(12,2);
    usagePercent            : Decimal(5,2);
    alertThreshold          : Integer;
    expirationDate          : Date;
    daysToExpiration        : Integer;
    environment             : String(20);   // Production, Development, QA
    lastUpdated             : DateTime;
}

// ─────────────────────────────────────────────
// RESTORED FROM RENTED SYSTEM: LicenseOptimization
// Licensed vs Active users — license waste detection
// ─────────────────────────────────────────────
entity LicenseOptimization {
    key ID                  : UUID;
    region                  : String(10);
    subaccount              : String(60);
    serviceName             : String(80);
    licenseType             : String(40);   // Named-User, PUPM, Developer, Base
    licensedUsers           : Integer;
    activeUsers             : Integer;
    unusedLicenses          : Integer;
    utilizationPercent      : Decimal(5,2);
    monthlyCostPerLicense   : Decimal(8,2);
    monthlyWastedCost       : Decimal(10,2);
    lastLoginDate           : Date;
    daysSinceLastLogin      : Integer;
    billingMonth            : String(8);
    recommendation          : String(200);
    status                  : String(20);   // Optimal, Review, Waste, Critical-Waste
}
