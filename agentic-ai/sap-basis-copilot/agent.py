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
    check_long_running_jobs
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
        check_long_running_jobs
    ]
)
