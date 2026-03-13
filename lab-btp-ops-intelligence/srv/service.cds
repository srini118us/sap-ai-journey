using { btp.intelligent.ops as my } from '../db/schema';

@path: '/service/btp-ops'
service BTPIntelligentOpsService {

    // ── TILE 1: Trust & Connectivity ──────────────────
    @readonly entity CertificatesHealth   as projection on my.CertificatesHealth;
    @readonly entity DestinationsHealth   as projection on my.DestinationsHealth;

    function getConnectivityKPI() returns {
        complianceScore     : Decimal(5,2);
        criticalCerts       : Integer;
        warningCerts        : Integer;
        unreachableDests    : Integer;
        expiryConvergence   : Boolean;
        convergenceWindow   : String(80);
        nextExpiryDays      : Integer;
        nextExpiryService   : String(80);
    };

    // ── TILE 2: Cloud Economics ────────────────────────
    @readonly entity CostConsumption      as projection on my.CostConsumption;

    function getCostKPI() returns {
        totalBudgetUSD      : Decimal(12,2);
        totalActualUSD      : Decimal(12,2);
        totalForecastUSD    : Decimal(12,2);
        overBudgetServices  : Integer;
        idleWasteUSD        : Decimal(10,2);
        idleServiceCount    : Integer;
        budgetRunOutDate    : String(20);
        burnRateDailyUSD    : Decimal(10,2);
        cpeaCreditsUsed     : Decimal(10,2);
    };

    // ── TILE 3: Compute Efficiency ────────────────────
    @readonly entity ComputeResources     as projection on my.ComputeResources;

    function getComputeKPI() returns {
        totalAllocatedGB    : Decimal(12,2);
        totalUsedGB         : Decimal(12,2);
        overallUsagePct     : Decimal(5,2);
        ghostSpaceCount     : Integer;
        ghostSpaceWasteUSD  : Decimal(10,2);
        criticalResources   : Integer;
        atRiskResources     : Integer;
        recoverableGB       : Decimal(10,2);
    };

    // ── TILE 4: Innovation & AI ROI ───────────────────
    @readonly entity AIActivityLog        as projection on my.AIActivityLog;

    function getAIROIKPI() returns {
        totalAIUnitsUsed    : Decimal(10,2);
        totalAICostUSD      : Decimal(10,4);
        manualHoursSaved    : Decimal(8,2);
        avgIntentSuccess    : Decimal(5,2);
        alertsAutoTriaged   : Integer;
        hoursSavedValueUSD  : Decimal(10,2);
        roiMultiplier       : Decimal(6,2);
    };

    // ── CROSS-CUTTING: Alerts & Recommendations ───────
    @readonly entity OperationalAlerts    as projection on my.OperationalAlerts;
    @readonly entity AIRecommendations    as projection on my.AIRecommendations;

    function getDashboardSummary() returns {
        criticalAlerts      : Integer;
        highAlerts          : Integer;
        openRecommendations : Integer;
        estimatedSavingsUSD : Decimal(12,2);
        overallHealthScore  : Decimal(5,2);
    };

    function getAlertsByRegion(region: String) returns array of {
        alertId     : String;
        severity    : String;
        title       : String;
        category    : String;
        status      : String;
        aiTriaged   : Boolean;
    };

    function getRecommendationsByPriority(priority: String) returns array of {
        recId           : String;
        category        : String;
        what            : String;
        why             : String;
        action          : String;
        savingUSD       : Decimal(10,2);
        effortHrs       : Decimal(5,1);
        affectedService : String;
    };

    // ── RESTORED: BTPServices + LicenseOptimization ──
    @readonly entity BTPServices          as projection on my.BTPServices;
    @readonly entity LicenseOptimization  as projection on my.LicenseOptimization;

    function getServicesAtRisk() returns array of {
        serviceId       : String;
        serviceName     : String;
        subaccount      : String;
        region          : String;
        usagePercent    : Decimal;
        status          : String;
        alertThreshold  : Integer;
        environment     : String;
    };

    function getLicenseWasteSummary() returns {
        totalLicensed         : Integer;
        totalActive           : Integer;
        totalUnused           : Integer;
        totalWastedUSD        : Decimal;
        criticalWasteCount    : Integer;
        overallUtilizationPct : Decimal;
    };
}
