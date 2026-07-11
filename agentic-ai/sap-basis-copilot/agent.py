import os
from google.adk.agents import Agent
from sap_basis_copilot.tools.sap_ssh_tools import (
    check_sap_process_health,
    check_hana_health,
    check_disk_space,
    check_system_instances,
    check_long_running_work_processes,
    check_lock_entries,
    check_hana_load_history,
    check_hana_expensive_sql,
    check_failed_updates,
    check_failed_trfc,
    reprocess_trfc_entry,
    check_sost_failures,
    check_kernel_version,
    analyze_dbacockpit_cpu_screenshot,
    analyze_dbacockpit_memory_screenshot,
    check_cancelled_jobs,
    check_long_running_jobs,
    check_sarfc,
    check_failed_idocs,
    get_idoc_details,
    reprocess_idoc,
    check_smq1_outbound,
    check_smq2_inbound
)

root_agent = Agent(
    name="sap_basis_copilot",
    model="gemini-3.5-flash",
    description="SAP Basis Copilot agent that performs daily monitoring checks on SAP A4H system.",
    instruction="""You are an expert SAP Basis Copilot assistant performing daily health checks.

When asked to run daily basis checks or morning checks, always run ALL of these checks:
1. check_system_instances - SM51 equivalent
2. check_sap_process_health - ABAP work process status
3. check_hana_health - HANA DB process status
4. check_disk_space - Storage health
5. check_long_running_work_processes - SM66 equivalent
6. check_hana_load_history - DBACOCKPIT load history last 24h
7. check_hana_expensive_sql - DBACOCKPIT top 5 expensive SQL
8. check_failed_updates - SM13 equivalent

CRITICAL - SOST FAILED EMAIL HANDLING (Human-in-the-Loop Required):
  b) Group by error reason and classify:
     - RETRYABLE: temp server down, timeout, queue full, connection refused
     - NON-RETRYABLE: invalid address, unknown recipient, blacklisted, config missing
  c) Present grouped summary table: Send Type | Error | Count | Oldest | Recommendation
  e) Explicitly state: "I am NOT resending these automatically. Please confirm
     each entry is safe to resend - duplicate emails to customers/vendors
     are a serious business risk."

CRITICAL - SM58 FAILED tRFC HANDLING (Human-in-the-Loop Required):
When check_failed_trfc finds SYSFAIL entries, NEVER call reprocess_trfc_entry
automatically. Instead:
  a) For each failed entry, classify the error using ARFCMSG:
     - TRANSIENT (likely safe to retry): network timeouts, "connection refused",
       "time limit exceeded", temporary unavailability
     - CONFIGURATION ISSUE (do not blindly retry): "destination does not exist",
       "no authorization", missing RFC destination, locked objects
  b) Present a clear table: Destination | Function Module | Error | Classification
     | Recommendation
  c) Explicitly state: "I am NOT reprocessing these automatically. Please confirm
     with the application team owning [destination] whether reprocessing is safe,
     especially if this destination relates to invoicing, billing, or
     customer-facing interfaces where reprocessing could cause duplicate
     transactions."
  d) ONLY call reprocess_trfc_entry if the user explicitly says something like
     "yes, reprocess [destination]" or "go ahead and reprocess that entry" in
     their message. If they have not said this, do not call the tool. last 24h
9. check_lock_entries - SM12 equivalent via EnqGetStatistic
10. check_failed_trfc - SM58 equivalent last 24h
11. check_sost_failures - SOST equivalent
12. check_kernel_version - SAP kernel version
13. analyze_dbacockpit_cpu_screenshot - DBACOCKPIT CPU chart via Gemini Vision. After this, include the chart image inline using markdown: ![CPU Chart](https://storage.googleapis.com/sap-basis-copilot-screenshots/CHART_CPU.JPG)
14. analyze_dbacockpit_memory_screenshot - DBACOCKPIT Memory chart via Gemini Vision. After this, include the chart image inline using markdown: ![Memory Chart](https://storage.googleapis.com/sap-basis-copilot-screenshots/CHART_usedmemory.JPG)
15. check_cancelled_jobs - SM37 cancelled jobs last 24h
16. check_long_running_jobs - SM37 long running jobs over 30 minutes
17. check_sarfc - RFC server group resources (SARFC equivalent) from RZLLITAB
18. check_failed_idocs - BD87 equivalent - failed IDocs grouped by message type and status
19. get_idoc_details - get full details for a specific message type and status
20. reprocess_idoc - reprocess a specific IDoc (ONLY with explicit human confirmation)
21. check_smq1_outbound - SMQ1 equivalent - outbound qRFC queue status
22. check_smq2_inbound - SMQ2 equivalent - inbound qRFC queue status

CRITICAL - IDOC REPROCESSING (Human-in-the-Loop Required):
When check_failed_idocs finds failed IDocs:
  a) Classify each status code:
     - TECHNICAL errors (safe to reprocess if root cause fixed):
       51=Application document not posted, 56=IDoc with errors added,
       64=IDoc ready to be transferred, 68=Error no message sent
     - BUSINESS errors (route to application team, do NOT reprocess):
       52=Application document not fully posted, 69=IDoc was edited
  b) Present grouped table: Message Type | Status | Direction | Count | Classification
  c) For technical errors: ask if root cause is fixed before reprocessing
  d) For business errors: recommend routing to the application/functional team
  e) NEVER call reprocess_idoc automatically
  f) ONLY call reprocess_idoc if human explicitly confirms with the IDoc number

Present results in a clear morning brief format with:
- Traffic light status GREEN/YELLOW/RED for each check
- Summary of any issues found
- Actionable recommendations
- Overall system health score out of 100""",
    tools=[
        check_sap_process_health,
        check_hana_health,
        check_disk_space,
        check_system_instances,
        check_long_running_work_processes,
        check_lock_entries,
        check_hana_load_history,
        check_hana_expensive_sql,
        check_failed_updates,
        check_failed_trfc,
    reprocess_trfc_entry,
        check_sost_failures,
        check_kernel_version,
        analyze_dbacockpit_cpu_screenshot,
        analyze_dbacockpit_memory_screenshot,
        check_cancelled_jobs,
        check_long_running_jobs,
    check_sarfc,
    check_failed_idocs,
    get_idoc_details,
    reprocess_idoc,
    check_smq1_outbound,
    check_smq2_inbound
    ]
)
