#!/usr/bin/env python3
"""
Generate 4 vendor Master Data Quality policy PDFs.

Output files (in policies/):
  01_vendor_mdg_policy.pdf              Vendor Master Data Governance Policy
  02_duplicate_detection_standard.pdf   Duplicate Vendor Detection Standard
  03_vendor_onboarding_compliance.pdf   Vendor Onboarding Compliance Requirements
  04_blocked_vendor_management.pdf      Blocked Vendor Management Procedure

Each policy references quality rule IDs (QR001 to QR030) from QUALITY_RULES table
so the copilot can cross reference policy sections with data findings.
"""

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from pathlib import Path

OUT = Path(__file__).parent / "policies"
OUT.mkdir(exist_ok=True)

# ==========================================================
# Shared styles
# ==========================================================
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'CustomTitle', parent=styles['Title'],
    fontSize=22, spaceAfter=8, alignment=TA_CENTER, textColor=colors.HexColor('#1F3864')
)
subtitle_style = ParagraphStyle(
    'CustomSubtitle', parent=styles['Normal'],
    fontSize=12, spaceAfter=20, alignment=TA_CENTER, textColor=colors.HexColor('#595959'),
    fontName='Helvetica-Oblique'
)
h1_style = ParagraphStyle(
    'CustomH1', parent=styles['Heading1'],
    fontSize=16, spaceBefore=16, spaceAfter=10, textColor=colors.HexColor('#1F3864')
)
h2_style = ParagraphStyle(
    'CustomH2', parent=styles['Heading2'],
    fontSize=13, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor('#2E5C99')
)
body_style = ParagraphStyle(
    'CustomBody', parent=styles['Normal'],
    fontSize=11, spaceAfter=8, alignment=TA_JUSTIFY, leading=15
)
bullet_style = ParagraphStyle(
    'CustomBullet', parent=styles['Normal'],
    fontSize=11, spaceAfter=4, leftIndent=20, bulletIndent=8, leading=14
)

def build_pdf(filename, title, subtitle, story_content):
    """Build a single PDF from title, subtitle, and content list."""
    filepath = OUT / filename
    doc = SimpleDocTemplate(
        str(filepath), pagesize=letter,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.75*inch, bottomMargin=0.75*inch
    )
    story = [
        Paragraph(title, title_style),
        Paragraph(subtitle, subtitle_style),
        Spacer(1, 12)
    ]
    story.extend(story_content)
    doc.build(story)
    return filepath

def p(text): return Paragraph(text, body_style)
def h1(text): return Paragraph(text, h1_style)
def h2(text): return Paragraph(text, h2_style)
def bl(text): return Paragraph("• " + text, bullet_style)

# ==========================================================
# POLICY 1: Vendor Master Data Governance Policy
# ==========================================================
policy_1 = [
    h1("1. Purpose and Scope"),
    p("This policy establishes governance standards for creating, maintaining, and retiring vendor master data records across the enterprise. It applies to all vendor records in the SAP master data domain including strategic suppliers, one time payees, intercompany vendors, and employee reimbursement records."),
    p("The policy is mandatory for all personnel involved in vendor lifecycle management including procurement, accounts payable, treasury, tax, compliance, and master data stewardship teams."),

    h1("2. Governance Principles"),
    p("Vendor master data is a critical enterprise asset that directly impacts financial reporting accuracy, tax compliance, payment integrity, and fraud prevention. All vendor records must meet the following foundational principles:"),
    bl("Completeness: All mandatory fields must be populated at record creation and maintained throughout the vendor lifecycle."),
    bl("Uniqueness: Every legal entity relationship must have exactly one vendor master record. Duplicate records create risk of duplicate payments and audit findings."),
    bl("Validity: Field values must conform to defined data types, code lists, and format standards including ISO country codes and approved payment terms."),
    bl("Consistency: Related fields must maintain logical relationships. Vendor status and transaction activity must be consistent."),
    bl("Timeliness: Records must be updated within defined service level agreements when supplier information changes."),

    h1("3. Mandatory Fields"),
    p("The following fields are mandatory for all ACTIVE vendor records. Rule QR001 enforces vendor name presence and QR002 enforces tax ID presence for active vendors."),
    h2("3.1 Identification"),
    bl("Vendor legal name (matching tax registration or equivalent legal document)"),
    bl("Tax identification number in country appropriate format"),
    bl("Registered business address including street, city, country ISO code, and postal code"),

    h2("3.2 Financial"),
    bl("Bank account number (validated per rule QR003, minimum 8 digits)"),
    bl("Currency (must be from approved currency list per rule QR030)"),
    bl("Payment terms (must match approved code list per rule QR007)"),

    h2("3.3 Classification"),
    bl("Vendor category (required per rule QR016 for spend analytics)"),
    bl("Description of goods or services provided"),

    h1("4. Data Steward Responsibilities"),
    p("The Master Data Governance team assigns a data steward to each vendor category. Stewards are responsible for the quality of records within their assigned domain."),
    h2("4.1 Daily Operations"),
    bl("Review the exception queue for records flagged by automated quality rules"),
    bl("Approve or reject vendor creation requests from procurement business partners"),
    bl("Perform root cause analysis on recurring quality issues"),

    h2("4.2 Periodic Reviews"),
    bl("Monthly: reconcile new vendor creations against onboarding checklist compliance"),
    bl("Quarterly: review high risk vendors flagged by rule QR008 (risk score above 0.8)"),
    bl("Annually: purge or archive vendors with no transaction activity for over three years (per rule QR009)"),

    h1("5. Risk Scoring Framework"),
    p("Each vendor is assigned a risk score between 0.00 and 1.00 based on the following weighted factors:"),
    bl("Country of registration (25% weight): sanctioned countries score 1.00 automatically"),
    bl("Payment history variance (20% weight): high dispute or reversal rates increase score"),
    bl("Category concentration (15% weight): single vendor exceeding 20% of category spend"),
    bl("Data quality issue frequency (15% weight): historical issue count in QUALITY_ISSUES"),
    bl("Compliance certification status (15% weight): missing or expired certifications increase score"),
    bl("Length of relationship (10% weight): new vendors score higher until history builds"),

    p("Vendors with risk scores above 0.80 (rule QR008) are subject to quarterly review by the procurement risk committee. Vendors above 0.95 require CFO approval for any transaction exceeding fifty thousand dollars."),

    h1("6. Data Change Management"),
    p("Any change to critical vendor master fields (name, address, bank account, tax ID) requires the following workflow:"),
    bl("Change request submitted through MDG application with supporting documentation"),
    bl("Automated validation checks against all applicable quality rules"),
    bl("Approval from assigned data steward and financial controller for bank changes"),
    bl("Notification to accounts payable and treasury teams of effective changes"),

    p("Rule QR027 detects rapid changes (within 24 hours of transaction posting) which trigger automatic audit review to prevent fraudulent modifications."),

    h1("7. Non Compliance Consequences"),
    p("Violations of this policy result in the following actions depending on severity:"),
    bl("CRITICAL severity (QR001, QR005, QR018): immediate transaction blocking and compliance escalation"),
    bl("HIGH severity (QR002, QR003, QR004, QR008, QR014, QR017, QR020, QR024): remediation required within 5 business days"),
    bl("MEDIUM severity: addressed in monthly cleanup batch"),
    bl("LOW severity: batched with quarterly review"),

    h1("8. Policy Ownership"),
    p("This policy is owned by the Enterprise Data Governance Office. Questions should be directed to the vendor master data governance team via the enterprise service desk. Annual review is performed each fiscal quarter one to reflect regulatory changes and lessons learned.")
]

build_pdf("01_vendor_mdg_policy.pdf",
          "Vendor Master Data Governance Policy",
          "Enterprise Data Governance Office | Version 4.2 | Effective 2026",
          policy_1)

# ==========================================================
# POLICY 2: Duplicate Vendor Detection Standard
# ==========================================================
policy_2 = [
    h1("1. Purpose"),
    p("This standard defines the methodology for detecting, evaluating, and resolving duplicate vendor master records. Duplicate vendors create risk of duplicate payments, distort spend analytics, and complicate vendor relationship management. Every duplicate pair identified must be evaluated within five business days of detection."),

    h1("2. Detection Criteria"),
    p("Rule QR004 automatically detects potential duplicate vendors based on the following criteria evaluated together:"),

    h2("2.1 Primary Match Criteria"),
    bl("Same address line 1 and same city: high confidence duplicate signal"),
    bl("Same tax identification number across multiple vendor records: definitive duplicate"),
    bl("Same bank account number (rule QR020): critical fraud risk requiring immediate freeze"),

    h2("2.2 Secondary Match Criteria"),
    bl("Similar vendor names within edit distance of 3 characters (LLC vs Ltd variations)"),
    bl("Same country and same postal code with similar names"),
    bl("Same primary contact person across records with different vendor IDs"),

    h2("2.3 Confidence Scoring"),
    p("Each candidate duplicate pair receives a confidence score based on how many match criteria are satisfied:"),
    bl("Score 0.95 to 1.00: automatic merge with data steward notification"),
    bl("Score 0.80 to 0.94: MDG workflow for steward review before merge"),
    bl("Score 0.60 to 0.79: added to weekly duplicate review queue"),
    bl("Score below 0.60: no action, monitored quarterly"),

    h1("3. MDG Workflow"),
    p("The Master Data Governance application executes the following workflow for confirmed duplicates:"),

    h2("3.1 Analysis Phase"),
    bl("Identify the surviving record based on: earliest created, most complete data, highest transaction volume"),
    bl("Compare all fields between records, flagging conflicts for steward decision"),
    bl("Report all open purchase orders, open invoices, and pending payments across both records"),

    h2("3.2 Consolidation Phase"),
    bl("Merge all historical transactions from retiring record into surviving record"),
    bl("Update all open documents to reference surviving vendor ID"),
    bl("Preserve full audit trail of the merge including original values"),
    bl("Retire duplicate record with status ARCHIVED and merge reference"),

    h2("3.3 Notification Phase"),
    bl("Email business owner of retiring vendor about the merge decision"),
    bl("Notify accounts payable team of vendor ID changes affecting open items"),
    bl("Update procurement analytics dashboards to reflect consolidated spend"),

    h1("4. Merge Prevention Rules"),
    p("The following situations prevent automated merge and require manual review:"),
    bl("Different countries: potentially separate legal entities of the same corporate group"),
    bl("Different currencies with active balances: FX implications require treasury review"),
    bl("Active disputes on either record: legal team review required before consolidation"),
    bl("Open regulatory investigations: compliance team clearance required"),

    h1("5. Prevention Controls"),
    p("The vendor onboarding process includes real time duplicate detection to prevent duplicate creation:"),
    bl("Fuzzy match on vendor name against existing active vendors during data entry"),
    bl("Tax ID uniqueness check across all vendor records regardless of status"),
    bl("Address validation with geocoding to normalize address variations"),
    bl("Bank account cross reference to identify shared banking relationships"),

    h1("6. Metrics and Reporting"),
    p("Master Data Governance reports the following metrics monthly to the data governance council:"),
    bl("Number of duplicate pairs detected"),
    bl("Number of merges completed and average cycle time"),
    bl("Estimated duplicate payment risk avoided (open items eliminated)"),
    bl("Root cause categorization: prevention improvement opportunities"),

    h1("7. Root Cause Categories"),
    p("Historical analysis of duplicates in the QUALITY_ISSUES table shows the following root cause distribution:"),
    bl("55% Vendor onboarding by different business units without cross checking"),
    bl("20% Corporate mergers introducing overlapping vendor bases"),
    bl("15% System migrations creating parallel records"),
    bl("10% Data entry errors in vendor name field creating apparent uniqueness"),

    h1("8. Related Standards"),
    p("This standard is enforced in conjunction with the Vendor Master Data Governance Policy (section 3 mandatory fields) and the Vendor Onboarding Compliance Requirements (section 4 duplicate check). Any exception to this standard requires approval from the Chief Data Officer.")
]

build_pdf("02_duplicate_detection_standard.pdf",
          "Duplicate Vendor Detection Standard",
          "Master Data Governance | Version 3.1 | Effective 2026",
          policy_2)

# ==========================================================
# POLICY 3: Vendor Onboarding Compliance Requirements
# ==========================================================
policy_3 = [
    h1("1. Scope"),
    p("This document specifies the compliance requirements that must be satisfied before any new vendor is activated in the vendor master. It applies to all vendor types including strategic suppliers, one time payees, professional services firms, and international vendors."),
    p("Failure to complete required steps blocks vendor activation and prevents any transaction processing. Emergency exceptions require CFO approval and are documented in the audit register."),

    h1("2. Required Documentation"),
    h2("2.1 Universal Requirements"),
    bl("Vendor registration form completed by requesting business unit"),
    bl("Tax certificate matching the tax identification number (rule QR002)"),
    bl("Bank account verification letter on vendor letterhead (rule QR003)"),
    bl("Insurance certificate where vendor performs on premises work"),

    h2("2.2 International Vendors"),
    bl("W-8 series form (for United States entities engaging non US vendors)"),
    bl("Country specific tax registration document"),
    bl("Beneficial ownership disclosure per FATF standards"),
    bl("Sanctions screening confirmation from compliance team"),

    h2("2.3 Regulated Categories"),
    bl("Financial services: regulatory license copies"),
    bl("Healthcare: HIPAA business associate agreement where applicable"),
    bl("Technology services: SOC 2 Type II report or equivalent"),
    bl("Data processing: data processing agreement per GDPR article 28"),

    h1("3. Onboarding Workflow"),
    h2("3.1 Request Phase"),
    p("Business partner submits vendor request through MDG application including all required documentation. System automatically validates:"),
    bl("All mandatory fields populated (rule QR001, QR002, QR016)"),
    bl("Tax ID format valid for stated country"),
    bl("Bank account format valid (rule QR003)"),
    bl("Country code is valid ISO 3166 three character code (rule QR006)"),

    h2("3.2 Compliance Screening"),
    p("Automated screening against the following watchlists occurs before human review:"),
    bl("OFAC Specially Designated Nationals and Blocked Persons list"),
    bl("EU consolidated sanctions list"),
    bl("UN Security Council sanctions committee lists"),
    bl("Local Politically Exposed Persons databases in vendor country"),
    bl("Debarred vendors list from World Bank and similar institutions"),

    p("Vendors in sanctioned countries (rule QR024) are automatically rejected and referred to compliance for review."),

    h2("3.3 Duplicate Prevention Check"),
    p("Per the Duplicate Vendor Detection Standard, real time duplicate detection runs against existing vendors. Matches above confidence 0.80 pause onboarding pending steward review."),

    h2("3.4 Approval Phase"),
    p("Depending on vendor risk profile, the following approval chain applies:"),
    bl("Standard risk (score below 0.5): auto approve if all validations pass"),
    bl("Medium risk (score 0.5 to 0.8): data steward approval required"),
    bl("High risk (score above 0.8, rule QR008): procurement risk committee review"),
    bl("Sanctioned country or watchlist hit: reject with compliance notification"),

    h1("4. Pending Status Management"),
    p("Vendors remain in PENDING status until all onboarding requirements are satisfied. Rule QR015 flags vendors in PENDING status for over 60 days for follow up. The requesting business partner receives escalation notifications at 30 days and 45 days."),

    h1("5. New Vendor Payment Controls"),
    p("Newly activated vendors are subject to enhanced controls for the first 90 days:"),
    bl("First payment requires physical or video confirmation of banking details"),
    bl("Rule QR014 flags payments over fifty thousand dollars to vendors created within 30 days for enhanced due diligence"),
    bl("Payments diverted to internal escrow account if any red flag is detected"),
    bl("Monthly review by AP team of all new vendor payment activity"),

    h1("6. Onboarding Metrics"),
    p("Success of vendor onboarding is measured monthly:"),
    bl("Cycle time from request to activation (target: under 10 business days)"),
    bl("Percentage of requests requiring rework due to incomplete documentation"),
    bl("Compliance rejection rate and root cause categorization"),
    bl("Post activation quality issue count within first 90 days"),

    h1("7. Exception Handling"),
    p("Emergency exceptions bypass standard workflow for urgent business need. Exception requirements:"),
    bl("Written justification from senior business leader (director or above)"),
    bl("CFO or delegate approval with documented business impact"),
    bl("Post exception review within 5 business days to complete standard steps"),
    bl("Audit register entry for annual compliance review"),

    h1("8. Related Documents"),
    p("This document should be read alongside the Vendor Master Data Governance Policy and the Duplicate Vendor Detection Standard. All three documents together define the complete vendor lifecycle governance framework.")
]

build_pdf("03_vendor_onboarding_compliance.pdf",
          "Vendor Onboarding Compliance Requirements",
          "Procurement and Compliance | Version 5.0 | Effective 2026",
          policy_3)

# ==========================================================
# POLICY 4: Blocked Vendor Management Procedure
# ==========================================================
policy_4 = [
    h1("1. Overview"),
    p("This procedure governs the lifecycle of blocked vendor records including blocking triggers, block enforcement, unblock workflow, and audit trail requirements. Effective blocked vendor management is a critical control against fraud, sanctions violations, and unauthorized payments."),
    p("Rule QR005 detects transactions posted against BLOCKED vendors and triggers immediate compliance escalation. Any override requires documented business justification and CFO approval."),

    h1("2. Blocking Triggers"),
    h2("2.1 Automatic Blocking"),
    p("The system automatically transitions vendor status to BLOCKED when any of the following triggers fire:"),
    bl("Sanctions list match confirmed by compliance screening"),
    bl("Country of registration added to sanctions or embargo list (rule QR024)"),
    bl("Duplicate bank account detected across multiple vendors (rule QR020)"),
    bl("Regulatory or legal order requiring payment freeze"),
    bl("Vendor bankruptcy or insolvency notification received"),

    h2("2.2 Manual Blocking"),
    p("Authorized personnel may request blocking through the MDG application. Common manual blocking reasons include:"),
    bl("Contract termination with unresolved disputes"),
    bl("Quality or performance issues requiring supplier action"),
    bl("Enhanced due diligence in progress for elevated risk"),
    bl("Suspected fraud pending investigation"),

    p("Manual blocking requires approval from procurement director or compliance officer."),

    h1("3. Block Enforcement"),
    h2("3.1 Transaction Prevention"),
    p("When vendor status is BLOCKED, the following transactions are prevented at source:"),
    bl("New purchase order creation for the vendor"),
    bl("Invoice posting against existing purchase orders"),
    bl("Payment run inclusion of any open items for the vendor"),
    bl("Master data changes except for status transition workflow"),

    h2("3.2 Exception Handling"),
    p("In rare emergency situations, business continuity may require processing a transaction for a blocked vendor. The exception process requires:"),
    bl("Business justification signed by senior leader (VP or above)"),
    bl("CFO or delegate approval with documented rationale"),
    bl("Compliance officer sign off on regulatory risk assessment"),
    bl("Enhanced audit trail preserving all approval documentation"),
    bl("Post transaction review within 24 hours"),

    p("Rule QR005 will flag these exception transactions and route them to audit review as CRITICAL severity issues. Historical exception analysis shows 90% of exceptions are subsequently found to be avoidable with better planning."),

    h1("4. Unblock Workflow"),
    p("Unblocking a vendor requires resolution of the original blocking cause and passage through review checkpoints."),

    h2("4.1 Preparation Phase"),
    bl("Document root cause of original block and resolution taken"),
    bl("Gather supporting evidence (updated compliance certificates, resolved disputes, court orders)"),
    bl("Business partner submits unblock request in MDG application"),

    h2("4.2 Review Phase"),
    p("The review checkpoints vary by original block reason:"),
    bl("Sanctions related: compliance team re screens vendor against current lists"),
    bl("Quality or performance: procurement lead validates supplier improvement"),
    bl("Fraud investigation: legal team confirmation of case closure"),
    bl("Bank account issue: treasury verification of corrected banking details"),

    h2("4.3 Approval Phase"),
    p("Approval authority depends on original block severity:"),
    bl("Sanctions or fraud origin: Chief Compliance Officer approval mandatory"),
    bl("Financial or bank issue: Treasurer approval"),
    bl("Performance or contractual: Procurement Director approval"),

    h2("4.4 Reactivation Phase"),
    bl("Status transitioned from BLOCKED to ACTIVE with enhanced monitoring flag"),
    bl("Enhanced monitoring applied for 6 months following reactivation"),
    bl("Quarterly attestation added to risk register during monitoring period"),
    bl("Business partner and AP team notified of reactivation with monitoring requirements"),

    h1("5. Enhanced Monitoring After Unblock"),
    p("Reactivated vendors are subject to enhanced controls for 180 days:"),
    bl("Every transaction requires two person approval regardless of amount"),
    bl("Payment amounts limited to under fifty thousand dollars per transaction without additional approval"),
    bl("Monthly compliance re screening for the monitoring period"),
    bl("Quarterly review by risk committee of transaction pattern"),

    h1("6. Audit Trail Requirements"),
    p("All blocking and unblocking events preserve the following audit information indefinitely:"),
    bl("Timestamp of status change"),
    bl("User ID initiating the change"),
    bl("Business justification and supporting documentation"),
    bl("Approval chain with timestamps at each approval"),
    bl("Compliance screening results at time of decision"),
    bl("Related quality issues and their resolutions"),

    h1("7. Metrics Reporting"),
    p("Monthly metrics to the risk committee include:"),
    bl("Number of vendors blocked in the period by trigger category"),
    bl("Number of vendors unblocked with average cycle time"),
    bl("Emergency exceptions processed with post review findings"),
    bl("Transactions to blocked vendors detected (rule QR005 violations)"),
    bl("Average time from blocking trigger to enforcement"),

    h1("8. Roles and Responsibilities"),
    p("Clear ownership prevents delays in blocking or unblocking:"),
    bl("Compliance Officer: sanctions screening, watchlist matches, regulatory blocks"),
    bl("Treasurer: bank account related blocks and unblocks"),
    bl("Procurement Director: performance and contractual blocks"),
    bl("Data Steward: technical execution of status transitions in MDG"),
    bl("Chief Data Officer: policy exceptions and unusual patterns"),
    bl("Internal Audit: annual review of blocked vendor management effectiveness"),

    h1("9. Related Policies"),
    p("This procedure operates alongside the Vendor Master Data Governance Policy, the Duplicate Vendor Detection Standard, and the Vendor Onboarding Compliance Requirements. Together they form the complete vendor lifecycle governance framework maintained by the Enterprise Data Governance Office.")
]

build_pdf("04_blocked_vendor_management.pdf",
          "Blocked Vendor Management Procedure",
          "Compliance and Treasury | Version 2.3 | Effective 2026",
          policy_4)

# ==========================================================
# Summary
# ==========================================================
print("=== Policy PDF generation complete ===")
for pdf in sorted(OUT.glob("*.pdf")):
    size_kb = pdf.stat().st_size / 1024
    print(f"  {pdf.name}: {size_kb:.1f} KB")
