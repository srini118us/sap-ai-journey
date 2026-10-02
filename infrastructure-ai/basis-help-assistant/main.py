import json
import argparse
from job_failure_agent import JobFailureAgent, SAPODataClient
from llm_client import get_llm_client
from dotenv import load_dotenv
load_dotenv()
def load_config(config_path: str = "config.json") -> dict:
    with open(config_path, 'r') as f:
        return json.load(f)

def run_interactive(agent: JobFailureAgent):
    print("\n" + "="*60)
    print("SAP Job Failure Agent - Interactive Mode")
    print("="*60)
    
    symptom = input("\nDescribe the issue (or press Enter for default): ").strip()
    if not symptom:
        symptom = "Investigate failed background jobs in the last 24 hours"
    
    print(f"\n🔍 Investigating: {symptom}\n")
    
    thread_id = "interactive_session"
    result = agent.run(symptom, thread_id)
    
    print("\n" + "-"*40)
    print("Messages:")
    for msg in result["messages"]:
        # Handle both dict and LangChain message objects
        if hasattr(msg, 'type'):
            role = msg.type  # LangChain: 'human', 'ai', 'system'
            content = msg.content
        else:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
        print(f"  [{role}] {content[:200]}...")
    
    if result["status"] == "awaiting_approval" and result["remediation"]:
        print("\n" + "="*60)
        print("⚠️  REMEDIATION REQUIRES APPROVAL")
        print("="*60)
        print(f"Action: {result['remediation']['action']}")
        print(f"Job: {result['remediation']['job_name']}")
        print(f"Safety Tier: {result['remediation']['safety_tier']}")
        print(f"Rationale: {result['remediation']['rationale']}")
        
        approval = input("\nApprove remediation? (yes/no): ").strip().lower()
        
        if approval in ("yes", "y", "approved"):
            print("\n✅ Executing remediation...")
            result = agent.approve_remediation(thread_id)
        else:
            print("\n❌ Remediation rejected.")
            result = agent.reject_remediation(thread_id)
    
    print("\n" + "="*60)
    print("FINAL REPORT")
    print("="*60)
    print(f"Status: {result['status']}")
    print(f"Jobs Analyzed: {len(result['failed_jobs'])}")
    if result['selected_job']:
        print(f"Selected Job: {result['selected_job']['job_name']}")
    if result['root_cause']:
        print(f"\nRoot Cause:\n{result['root_cause'][:500]}")
    print("="*60 + "\n")

def run_batch(agent: JobFailureAgent, output_file: str = None):
    symptom = "Automated scan: Investigate all failed jobs in last 24 hours"
    result = agent.run(symptom, "batch_run")
    
    report = {
        "timestamp": str(__import__('datetime').datetime.utcnow()),
        "status": result["status"],
        "jobs_found": len(result["failed_jobs"]),
        "failed_jobs": result["failed_jobs"],
        "selected_job": result.get("selected_job"),
        "root_cause": result.get("root_cause"),
        "remediation_proposed": result.get("remediation")
    }
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Report saved to: {output_file}")
    else:
        print(json.dumps(report, indent=2, default=str))

def main():
    parser = argparse.ArgumentParser(description="SAP Job Failure Agent")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--mode", choices=["interactive", "batch"], default="interactive")
    parser.add_argument("--output", help="Output file for batch mode")
    parser.add_argument("--mock", action="store_true", help="Use mock clients for testing")
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    if args.mock:
        odata_client = MockODataClient()
        llm_client = get_llm_client("mock")
    else:
        odata_config = config["sap_odata"]
        odata_client = SAPODataClient(
            base_url=odata_config["base_url"],
            username=odata_config["username"],
            password=odata_config["password"]
        )
        
        ai_config = config.get("ai_core", {})
        llm_client = get_llm_client(
            mode=ai_config.get("mode", "mock"),
            model_name=ai_config.get("model_name", "gpt-4o")
        )
    
    agent = JobFailureAgent(odata_client, llm_client)
    
    if args.mode == "interactive":
        run_interactive(agent)
    else:
        run_batch(agent, args.output)

class MockODataClient:
    def get_failed_jobs(self, hours_back: int = 24) -> list[dict]:
        return [
            {
                "JobName": "ZMONTHEND_CLOSE",
                "JobRunCount": "00012345",
                "JobText": "Month End Close - Finance",
                "JobRunStatusText": "Canceled",
                "JobRunStartDatetime": "/Date(1712160000000)/",
                "JobRunEndDatetime": "/Date(1712163600000)/",
                "JobRunHasErrorInd": "X",
                "CanRestartJob": True,
                "JobTemplateName": "SAP_FI_MONTHEND",
                "JobCreatedByFormattedName": "BATCH_USER"
            },
            {
                "JobName": "ZBILLING_RUN",
                "JobRunCount": "00054321",
                "JobText": "Daily Billing Run",
                "JobRunStatusText": "Canceled",
                "JobRunStartDatetime": "/Date(1712150000000)/",
                "JobRunEndDatetime": "/Date(1712151800000)/",
                "JobRunHasErrorInd": "X",
                "CanRestartJob": True,
                "JobTemplateName": "SAP_SD_BILLING",
                "JobCreatedByFormattedName": "BATCH_USER"
            }
        ]
    
    def get_job_details(self, job_name: str, job_run_count: str) -> dict:
        return {
            "JobName": job_name,
            "JobRunCount": job_run_count,
            "JobText": "Month End Close - Finance",
            "JobRunStatus": "A",
            "JobRunStatusText": "Canceled"
        }
    
    def get_job_log(self, job_name: str, job_run_count: str) -> list[dict]:
        return [
            {"Timestamp": "/Date(1712160000000)/", "MsgType": "S", "MsgText": "Job started"},
            {"Timestamp": "/Date(1712161000000)/", "MsgType": "I", "MsgText": "Processing company code 1000"},
            {"Timestamp": "/Date(1712162000000)/", "MsgType": "W", "MsgText": "Warning: Large dataset detected"},
            {"Timestamp": "/Date(1712163000000)/", "MsgType": "E", "MsgText": "RFC connection to CLNT100 failed: COMMUNICATION_FAILURE"},
            {"Timestamp": "/Date(1712163500000)/", "MsgType": "A", "MsgText": "Job terminated due to error"}
        ]
    
    def get_application_log(self, log_handle: str) -> list[dict]:
        return []
    
    def restart_job(self, job_name: str, job_run_count: str, restart_mode: str = 'I') -> dict:
        print(f"[MOCK] Restarting job {job_name} with count {job_run_count}")
        return {"Successful": True}

if __name__ == "__main__":
    main()
