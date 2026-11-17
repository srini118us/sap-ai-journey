import os, re, base64, requests
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP

BASE  = "https://ec8c82aetrial.it-cpitrial03.cfapps.ap21.hana.ondemand.com"
TOKEN = "https://ec8c82aetrial.authentication.ap21.hana.ondemand.com/oauth/token"

# error pattern -> likely fix
FIXES = [
    (r"EDMX Fetch failed|Response Code:404|does not exist",
     "Receiver app or route is down. Start the CAP app in Cloud Foundry and recheck the OData address."),
    (r"Property value not found for the parameter",
     "A header or property was dropped. Add it to Allowed Headers in Runtime Configuration."),
    (r"401|invalid_client|Unauthorized", "Auth failure. Check credentials, token URL, and scope."),
    (r"403|Forbidden", "Authorization failure. Check role or scope on the receiver."),
    (r"Connection refused|timed out|UnknownHost", "Downstream unreachable. Check host, port, Cloud Connector."),
    (r"CSRF", "CSRF handling mismatch. Toggle CSRF on the receiver adapter."),
]

def fix_for(err):
    for pat, advice in FIXES:
        if re.search(pat, err, re.I):
            return advice
    return "No known pattern. Inspect the full trace in the Monitor."

def when(v):
    ms = int(re.search(r"\d+", v).group())
    return datetime.fromtimestamp(ms/1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def token():
    cid, sec = os.environ["CPI_CLIENTID"], os.environ["CPI_CLIENTSECRET"]
    b64 = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    return requests.post(TOKEN, headers={"Authorization": f"Basic {b64}"},
                         data={"grant_type": "client_credentials"}).json()["access_token"]

mcp = FastMCP("cpi-monitor")

@mcp.tool()
def list_failed_messages(top: int = 20) -> str:
    """List failed SAP Cloud Integration messages with timestamp, iFlow, error, and likely fix."""
    H = {"Authorization": f"Bearer {token()}", "Accept": "application/json"}
    url = (f"{BASE}/api/v1/MessageProcessingLogs"
           f"?$filter=Status eq 'FAILED'&$top={top}&$orderby=LogEnd desc")
    rows = requests.get(url, headers=H).json()["d"]["results"]
    if not rows:
        return "No failed messages."
    out = [f"Failed messages: {len(rows)}"]
    for m in rows:
        g = m["MessageGuid"]
        err = requests.get(f"{BASE}/api/v1/MessageProcessingLogs('{g}')/ErrorInformation/$value",
                           headers=H).text.strip()
        out.append(f"\n{when(m['LogEnd'])} UTC  {m['IntegrationFlowName']}")
        out.append(f"  Error: {err.splitlines()[0][:160]}")
        out.append(f"  Fix  : {fix_for(err)}")
    return "\n".join(out)

if __name__ == "__main__":
    mcp.run()