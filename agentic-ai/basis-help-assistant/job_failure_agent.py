from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
import requests
from datetime import datetime, timedelta
import json

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    symptom: str
    failed_jobs: list[dict]
    selected_job: dict | None
    job_log: list[dict]
    analysis: str
    root_cause: str
    remediation: dict | None
    awaiting_approval: bool
    status: Literal["investigating", "awaiting_approval", "executing", "complete", "stuck"]

class SAPODataClient:
    def __init__(self, base_url: str, username: str, password: str, client: str = "100"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'sap-client': client
        })
    
    def _fetch_csrf_token(self):
        response = self.session.get(
            f"{self.base_url}/$metadata",
            headers={'X-CSRF-Token': 'Fetch'}
        )
        return response.headers.get('X-CSRF-Token')
    
    def get_failed_jobs(self, hours_back: int = 48) -> list[dict]:
        # Use 'C' for Canceled status (failed jobs in SAP)
        # SAP Status codes: S=Scheduled, R=Released, Y=Ready, A=Active, F=Finished, C=Canceled
        filter_date = (datetime.utcnow() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%S")
        
        # Query all users by not filtering on JobCreatedByUser
        # Some SAP OData services need explicit $search or no user filter to return all
        url = (
            f"{self.base_url}/JobRunOverviewSet"
            f"?$filter=JobRunStatus eq 'C'"  # Just status, no date filter for now
            f"&$orderby=JobRunEndDatetime desc"
            f"&$top=50"
        )
        print(f"[DEBUG] OData URL: {url}")
        print(f"[DEBUG] Headers: {dict(self.session.headers)}")
        
        try:
            response = self.session.get(url)
            print(f"[DEBUG] Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[DEBUG] Response body: {response.text[:500]}")
                response.raise_for_status()
            
            data = response.json()
            results = data.get('d', {}).get('results', [])
            print(f"[DEBUG] Found {len(results)} canceled jobs")
            
            # Print first job for debugging
            if results:
                print(f"[DEBUG] First job: {results[0].get('JobName')} by {results[0].get('JobCreatedByUser', 'N/A')}")
            
            return results
        except Exception as e:
            print(f"[DEBUG] Error: {e}")
            raise
    
    def get_job_details(self, job_name: str, job_run_count: str) -> dict:
        url = f"{self.base_url}/JobRunDetailsSet(JobName='{job_name}',JobRunCount='{job_run_count}')"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json().get('d', {})
    
    def get_job_log(self, job_name: str, job_run_count: str) -> list[dict]:
        url = (
            f"{self.base_url}/JobRunLogSet"
            f"?$filter=JobName eq '{job_name}' and JobRunCount eq '{job_run_count}'"
            f"&$orderby=JobLogNumber asc"
        )
        response = self.session.get(url)
        response.raise_for_status()
        return response.json().get('d', {}).get('results', [])
    
    def get_application_log(self, log_handle: str) -> list[dict]:
        url = (
            f"{self.base_url}/ApplicationLogMessageSet"
            f"?$filter=LogHandle eq '{log_handle}'"
            f"&$orderby=MessageNumber asc"
        )
        response = self.session.get(url)
        response.raise_for_status()
        return response.json().get('d', {}).get('results', [])
    
    def restart_job(self, job_name: str, job_run_count: str, restart_mode: str = 'I') -> dict:
        csrf_token = self._fetch_csrf_token()
        url = (
            f"{self.base_url}/RestartJob"
            f"?JobName='{job_name}'"
            f"&JobRunCount='{job_run_count}'"
            f"&JobRestartMode='{restart_mode}'"
        )
        response = self.session.post(url, headers={'X-CSRF-Token': csrf_token})
        response.raise_for_status()
        return response.json().get('d', {})

class JobFailureAgent:
    def __init__(self, odata_client: SAPODataClient, llm_client):
        self.odata = odata_client
        self.llm = llm_client
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        
        workflow.add_node("fetch_failed_jobs", self.fetch_failed_jobs)
        workflow.add_node("analyze_job", self.analyze_job)
        workflow.add_node("fetch_job_log", self.fetch_job_log)
        workflow.add_node("diagnose_root_cause", self.diagnose_root_cause)
        workflow.add_node("propose_remediation", self.propose_remediation)
        workflow.add_node("report_findings", self.report_findings)
        
        workflow.set_entry_point("fetch_failed_jobs")
        
        workflow.add_edge("fetch_failed_jobs", "analyze_job")
        workflow.add_conditional_edges(
            "analyze_job",
            self.route_after_analysis,
            {
                "fetch_log": "fetch_job_log",
                "no_failures": "report_findings"
            }
        )
        workflow.add_edge("fetch_job_log", "diagnose_root_cause")
        workflow.add_edge("diagnose_root_cause", "propose_remediation")
        workflow.add_edge("propose_remediation", "report_findings")
        workflow.add_edge("report_findings", END)
        
        return workflow.compile(checkpointer=MemorySaver())
    
    def fetch_failed_jobs(self, state: AgentState) -> AgentState:
        failed_jobs = self.odata.get_failed_jobs(hours_back=24)
        formatted_jobs = []
        for job in failed_jobs:
            formatted_jobs.append({
                "job_name": job.get("JobName"),
                "job_run_count": job.get("JobRunCount"),
                "job_text": job.get("JobText"),
                "status": job.get("JobRunStatusText"),
                "start_time": job.get("JobRunStartDatetime"),
                "end_time": job.get("JobRunEndDatetime"),
                "has_error": job.get("JobRunHasErrorInd"),
                "can_restart": job.get("CanRestartJob"),
                "template_name": job.get("JobTemplateName"),
                "created_by": job.get("JobCreatedByFormattedName")
            })
        return {
            **state,
            "failed_jobs": formatted_jobs,
            "status": "investigating",
            "messages": state["messages"] + [{"role": "assistant", "content": f"Found {len(formatted_jobs)} failed jobs in the last 24 hours."}]
        }
    
    def analyze_job(self, state: AgentState) -> AgentState:
        if not state["failed_jobs"]:
            return {
                **state,
                "selected_job": None,
                "analysis": "No failed jobs found in the specified time range.",
                "messages": state["messages"] + [{"role": "assistant", "content": "No failed jobs to analyze."}]
            }
        
        selected = state["failed_jobs"][0]
        analysis = f"Analyzing job: {selected['job_text']} ({selected['job_name']})"
        
        return {
            **state,
            "selected_job": selected,
            "analysis": analysis,
            "messages": state["messages"] + [{"role": "assistant", "content": analysis}]
        }
    
    def route_after_analysis(self, state: AgentState) -> str:
        if state["selected_job"] is None:
            return "no_failures"
        return "fetch_log"
    
    def fetch_job_log(self, state: AgentState) -> AgentState:
        job = state["selected_job"]
        job_log = self.odata.get_job_log(job["job_name"], job["job_run_count"])
        
        formatted_log = []
        for entry in job_log:
            formatted_log.append({
                "timestamp": entry.get("Timestamp"),
                "msg_type": entry.get("MsgType"),
                "msg_text": entry.get("MsgText")
            })
        
        return {
            **state,
            "job_log": formatted_log,
            "messages": state["messages"] + [{"role": "assistant", "content": f"Retrieved {len(formatted_log)} log entries."}]
        }
    
    def diagnose_root_cause(self, state: AgentState) -> AgentState:
        job = state["selected_job"]
        log_entries = state["job_log"]
        
        error_messages = [e for e in log_entries if e.get("msg_type") in ("E", "A", "X")]
        
        prompt = f"""Analyze this SAP job failure and determine the root cause.

Job: {job['job_text']} ({job['job_name']})
Template: {job.get('template_name', 'N/A')}
Start: {job['start_time']}
End: {job['end_time']}

Error Log Entries:
{json.dumps(error_messages, indent=2)}

Provide a concise root cause analysis. Consider common SAP job failure causes:
- Authorization issues
- RFC connection failures
- Data inconsistencies
- Lock conflicts
- Resource exhaustion
- Missing master data
"""
        
        root_cause = self.llm.invoke(prompt)
        
        return {
            **state,
            "root_cause": root_cause,
            "messages": state["messages"] + [{"role": "assistant", "content": f"Root cause identified: {root_cause[:200]}..."}]
        }
    
    def propose_remediation(self, state: AgentState) -> AgentState:
        job = state["selected_job"]
        root_cause = state["root_cause"]
        
        if not job.get("can_restart"):
            return {
                **state,
                "remediation": None,
                "awaiting_approval": False,
                "status": "no_action_possible",
                "messages": state["messages"] + [{"role": "assistant", "content": "Job cannot be restarted. Manual intervention required."}]
            }
        
        remediation = {
            "action": "restart_job",
            "job_name": job["job_name"],
            "job_run_count": job["job_run_count"],
            "restart_mode": "I",
            "safety_tier": "yellow",
            "rationale": f"Based on root cause: {root_cause[:100]}..."
        }
        
        return {
            **state,
            "remediation": remediation,
            "awaiting_approval": True,
            "status": "awaiting_approval",
            "messages": state["messages"] + [{"role": "assistant", "content": f"Proposed remediation: Restart job {job['job_name']}. Awaiting approval."}]
        }
    
    def execute_remediation(self, state: AgentState) -> AgentState:
        remediation = state["remediation"]
        
        try:
            result = self.odata.restart_job(
                remediation["job_name"],
                remediation["job_run_count"],
                remediation["restart_mode"]
            )
            success = result.get("Successful", False)
            message = f"Job restart {'successful' if success else 'failed'}."
        except Exception as e:
            success = False
            message = f"Job restart failed: {str(e)}"
        
        return {
            **state,
            "status": "complete" if success else "stuck",
            "messages": state["messages"] + [{"role": "assistant", "content": message}]
        }
    
    def report_findings(self, state: AgentState) -> AgentState:
        selected_job = state.get("selected_job")
        report = {
            "symptom": state.get("symptom", "Job failure investigation"),
            "jobs_analyzed": len(state.get("failed_jobs", [])),
            "selected_job": selected_job.get("job_name") if selected_job else None,
            "root_cause": state.get("root_cause"),
            "remediation_proposed": state.get("remediation"),
            "final_status": state.get("status")
        }
        
        return {
            **state,
            "status": "complete",
            "messages": state["messages"] + [{"role": "assistant", "content": f"Investigation complete.\n{json.dumps(report, indent=2)}"}]
        }
    
    def run(self, symptom: str, thread_id: str = "default") -> AgentState:
        initial_state: AgentState = {
            "messages": [{"role": "user", "content": symptom}],
            "symptom": symptom,
            "failed_jobs": [],
            "selected_job": None,
            "job_log": [],
            "analysis": "",
            "root_cause": "",
            "remediation": None,
            "awaiting_approval": False,
            "status": "investigating"
        }
        
        config = {"configurable": {"thread_id": thread_id}}
        return self.graph.invoke(initial_state, config)
    
    def approve_remediation(self, thread_id: str) -> AgentState:
        config = {"configurable": {"thread_id": thread_id}}
        current_state = self.graph.get_state(config)
        
        updated_state = {
            **current_state.values,
            "awaiting_approval": False,
            "messages": current_state.values["messages"] + [{"role": "user", "content": "Approved"}]
        }
        
        return self.graph.invoke(updated_state, config)
    
    def reject_remediation(self, thread_id: str) -> AgentState:
        config = {"configurable": {"thread_id": thread_id}}
        current_state = self.graph.get_state(config)
        
        updated_state = {
            **current_state.values,
            "awaiting_approval": False,
            "messages": current_state.values["messages"] + [{"role": "user", "content": "Rejected"}]
        }
        
        return self.graph.invoke(updated_state, config)
