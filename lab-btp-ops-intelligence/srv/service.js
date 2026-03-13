'use strict';

const cds = require('@sap/cds');

module.exports = cds.service.impl(async function () {

    const {
        CertificatesHealth, DestinationsHealth,
        CostConsumption, ComputeResources,
        AIActivityLog, OperationalAlerts, AIRecommendations,
        BTPServices, LicenseOptimization
    } = this.entities;

    // ─────────────────────────────────────────────────────────
    // TILE 1: Trust & Connectivity KPI
    // ─────────────────────────────────────────────────────────
    this.on('getConnectivityKPI', async () => {
        const certs = await SELECT.from(CertificatesHealth);
        const dests = await SELECT.from(DestinationsHealth);

        const criticalCerts = certs.filter(c => c.status === 'Critical' || c.status === 'Expired');
        const warningCerts  = certs.filter(c => c.status === 'Warning');
        const unreachable   = dests.filter(d => d.status === 'Unreachable');
        const totalChecked  = certs.length + dests.length;
        const issues        = criticalCerts.length + warningCerts.length + unreachable.length;
        const complianceScore = totalChecked > 0
            ? (((totalChecked - issues) / totalChecked) * 100).toFixed(2)
            : 100;

        const critExpiring = certs
            .filter(c => c.daysToExpiry >= 0 && c.daysToExpiry <= 21)
            .sort((a, b) => a.daysToExpiry - b.daysToExpiry);

        let expiryConvergence = false;
        let convergenceWindow = '';
        if (critExpiring.length >= 2) {
            const windowSpread = critExpiring[critExpiring.length - 1].daysToExpiry - critExpiring[0].daysToExpiry;
            if (windowSpread <= 7) {
                expiryConvergence = true;
                convergenceWindow = `${critExpiring.length} certs expire within ${windowSpread} days of each other (${critExpiring[0].daysToExpiry}-${critExpiring[critExpiring.length - 1].daysToExpiry} days)`;
            }
        }

        const nextExpiring = certs
            .filter(c => c.daysToExpiry > 0)
            .sort((a, b) => a.daysToExpiry - b.daysToExpiry)[0];

        return {
            complianceScore   : parseFloat(complianceScore),
            criticalCerts     : criticalCerts.length,
            warningCerts      : warningCerts.length,
            unreachableDests  : unreachable.length,
            expiryConvergence,
            convergenceWindow,
            nextExpiryDays    : nextExpiring?.daysToExpiry ?? 0,
            nextExpiryService : nextExpiring?.associatedService ?? 'N/A'
        };
    });

    // ─────────────────────────────────────────────────────────
    // TILE 2: Cloud Economics KPI
    // ─────────────────────────────────────────────────────────
    this.on('getCostKPI', async () => {
        const costs = await SELECT.from(CostConsumption);

        const totalBudget   = costs.reduce((s, c) => s + (c.allocatedBudgetUSD || 0), 0);
        const totalActual   = costs.reduce((s, c) => s + (c.actualSpendUSD || 0), 0);
        const totalForecast = costs.reduce((s, c) => s + (c.forecastedSpendUSD || 0), 0);
        const overBudget    = costs.filter(c => (c.forecastedSpendUSD || 0) > (c.allocatedBudgetUSD || 0));
        const idleServices  = costs.filter(c => c.isIdle);
        const idleWaste     = idleServices.reduce((s, c) => s + (c.actualSpendUSD || 0), 0);
        const cpeaTotal     = costs.reduce((s, c) => s + (c.creditUnitsUsed || 0), 0);

        const today           = new Date();
        const dayOfMonth      = today.getDate();
        const burnRateDaily   = totalActual / dayOfMonth;
        const remainingBudget = totalBudget - totalActual;
        let budgetRunOutDate  = 'Within Budget';
        if (totalForecast > totalBudget) {
            const daysToExhaust = remainingBudget > 0 ? Math.floor(remainingBudget / burnRateDaily) : 0;
            const runOut = new Date(today);
            runOut.setDate(today.getDate() + daysToExhaust);
            budgetRunOutDate = daysToExhaust <= 0
                ? 'Budget Exceeded'
                : runOut.toISOString().split('T')[0];
        }

        return {
            totalBudgetUSD     : parseFloat(totalBudget.toFixed(2)),
            totalActualUSD     : parseFloat(totalActual.toFixed(2)),
            totalForecastUSD   : parseFloat(totalForecast.toFixed(2)),
            overBudgetServices : overBudget.length,
            idleWasteUSD       : parseFloat(idleWaste.toFixed(2)),
            idleServiceCount   : idleServices.length,
            budgetRunOutDate,
            burnRateDailyUSD   : parseFloat(burnRateDaily.toFixed(2)),
            cpeaCreditsUsed    : parseFloat(cpeaTotal.toFixed(2))
        };
    });

    // ─────────────────────────────────────────────────────────
    // TILE 3: Compute Efficiency KPI
    // ─────────────────────────────────────────────────────────
    this.on('getComputeKPI', async () => {
        const resources = await SELECT.from(ComputeResources);

        const totalAllocated = resources.reduce((s, r) => s + (r.allocatedGB || 0), 0);
        const totalUsed      = resources.reduce((s, r) => s + (r.usedGB || 0), 0);
        const overallPct     = totalAllocated > 0 ? (totalUsed / totalAllocated) * 100 : 0;
        const ghosts         = resources.filter(r => r.isGhostSpace);
        const ghostWaste     = ghosts.reduce((s, r) => s + (r.monthlyCostUSD || 0), 0);
        const critical       = resources.filter(r => r.status === 'Critical');
        const atRisk         = resources.filter(r => r.status === 'AtRisk');
        const recoverableGB  = ghosts.reduce((s, r) => s + (r.allocatedGB || 0), 0);

        return {
            totalAllocatedGB   : parseFloat(totalAllocated.toFixed(2)),
            totalUsedGB        : parseFloat(totalUsed.toFixed(2)),
            overallUsagePct    : parseFloat(overallPct.toFixed(2)),
            ghostSpaceCount    : ghosts.length,
            ghostSpaceWasteUSD : parseFloat(ghostWaste.toFixed(2)),
            criticalResources  : critical.length,
            atRiskResources    : atRisk.length,
            recoverableGB      : parseFloat(recoverableGB.toFixed(2))
        };
    });

    // ─────────────────────────────────────────────────────────
    // TILE 4: Innovation & AI ROI KPI
    // ─────────────────────────────────────────────────────────
    this.on('getAIROIKPI', async () => {
        const aiLogs = await SELECT.from(AIActivityLog);
        const alerts = await SELECT.from(OperationalAlerts);

        const totalUnits  = aiLogs.reduce((s, a) => s + (a.aiUnitsConsumed || 0), 0);
        const totalCost   = aiLogs.reduce((s, a) => s + (a.totalCostUSD || 0), 0);
        const hoursSaved  = aiLogs.reduce((s, a) => s + (a.manualHoursReplaced || 0), 0);
        const avgSuccess  = aiLogs.length > 0
            ? aiLogs.reduce((s, a) => s + (a.intentSuccessRate || 0), 0) / aiLogs.length
            : 0;
        const autoTriaged     = alerts.filter(a => a.isAutoTriaged).length;
        const HOURLY_RATE     = 150;
        const hoursSavedValue = hoursSaved * HOURLY_RATE;
        const roiMultiplier   = totalCost > 0 ? hoursSavedValue / totalCost : 0;

        return {
            totalAIUnitsUsed   : parseFloat(totalUnits.toFixed(2)),
            totalAICostUSD     : parseFloat(totalCost.toFixed(4)),
            manualHoursSaved   : parseFloat(hoursSaved.toFixed(2)),
            avgIntentSuccess   : parseFloat(avgSuccess.toFixed(2)),
            alertsAutoTriaged  : autoTriaged,
            hoursSavedValueUSD : parseFloat(hoursSavedValue.toFixed(2)),
            roiMultiplier      : parseFloat(roiMultiplier.toFixed(2))
        };
    });

    // ─────────────────────────────────────────────────────────
    // Dashboard Summary Header
    // ─────────────────────────────────────────────────────────
    this.on('getDashboardSummary', async () => {
        const alerts = await SELECT.from(OperationalAlerts);
        const recs   = await SELECT.from(AIRecommendations);

        const critical = alerts.filter(a => a.severity === 'Critical' && a.status !== 'Resolved');
        const high     = alerts.filter(a => a.severity === 'High' && a.status !== 'Resolved');
        const openRecs = recs.filter(r => r.status === 'New' || r.status === 'Accepted');
        const savings  = openRecs.reduce((s, r) => s + (r.estimatedSavingUSD || 0), 0);

        let healthScore = 100;
        healthScore -= (critical.length * 15);
        healthScore -= (high.length * 8);
        healthScore = Math.max(0, Math.min(100, healthScore));

        return {
            criticalAlerts      : critical.length,
            highAlerts          : high.length,
            openRecommendations : openRecs.length,
            estimatedSavingsUSD : parseFloat(savings.toFixed(2)),
            overallHealthScore  : parseFloat(healthScore.toFixed(2))
        };
    });

    // ─────────────────────────────────────────────────────────
    // Filtered Views
    // ─────────────────────────────────────────────────────────
    this.on('getAlertsByRegion', async (req) => {
        const { region } = req.data;
        const alerts = await SELECT.from(OperationalAlerts).where({ region });
        return alerts.map(a => ({
            alertId   : a.ID,
            severity  : a.severity,
            title     : a.title,
            category  : a.alertCategory,
            status    : a.status,
            aiTriaged : a.isAutoTriaged
        }));
    });

    this.on('getRecommendationsByPriority', async (req) => {
        const { priority } = req.data;
        const recs = await SELECT.from(AIRecommendations).where({ priority });
        return recs.map(r => ({
            recId           : r.ID,
            category        : r.category,
            what            : r.what,
            why             : r.why,
            action          : r.action,
            savingUSD       : r.estimatedSavingUSD,
            effortHrs       : r.estimatedEffortHrs,
            affectedService : r.affectedService
        }));
    });

    // ─────────────────────────────────────────────────────────
    // Services at Risk
    // ─────────────────────────────────────────────────────────
    this.on('getServicesAtRisk', async () => {
        const services = await SELECT.from(BTPServices);
        return services
            .filter(s => s.usagePercent >= s.alertThreshold || s.status === 'Critical' || s.status === 'Inactive')
            .sort((a, b) => b.usagePercent - a.usagePercent)
            .map(s => ({
                serviceId      : s.ID,
                serviceName    : s.serviceName,
                subaccount     : s.subaccount,
                region         : s.region,
                usagePercent   : s.usagePercent,
                status         : s.status,
                alertThreshold : s.alertThreshold,
                environment    : s.environment
            }));
    });

    // ─────────────────────────────────────────────────────────
    // License Waste Summary
    // ─────────────────────────────────────────────────────────
    this.on('getLicenseWasteSummary', async () => {
        const licenses = await SELECT.from(LicenseOptimization);

        const totalLicensed = licenses.reduce((s, l) => s + (l.licensedUsers || 0), 0);
        const totalActive   = licenses.reduce((s, l) => s + (l.activeUsers || 0), 0);
        const totalUnused   = licenses.reduce((s, l) => s + (l.unusedLicenses || 0), 0);
        const totalWasted   = licenses.reduce((s, l) => s + (l.monthlyWastedCost || 0), 0);
        const criticalWaste = licenses.filter(l => l.status === 'Critical-Waste').length;
        const overallUtil   = totalLicensed > 0 ? (totalActive / totalLicensed) * 100 : 0;

        return {
            totalLicensed,
            totalActive,
            totalUnused,
            totalWastedUSD        : parseFloat(totalWasted.toFixed(2)),
            criticalWasteCount    : criticalWaste,
            overallUtilizationPct : parseFloat(overallUtil.toFixed(2))
        };
    });

});
