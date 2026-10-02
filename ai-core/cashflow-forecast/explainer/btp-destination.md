# BTP Destination — sap-mcp-cashflow

Create this in the same BTP subaccount where Joule Studio runs
(rental: sap-btp-joule, us10).

Path: BTP Cockpit → Subaccount → Connectivity → Destinations → New Destination

## Properties

| Field | Value |
|---|---|
| Name | sap-mcp-cashflow |
| Type | HTTP |
| Description | MCP server for cashflow forecast explainability — Tools: explain_cashflow_full, explain_cashflow_template |
| URL | https://sap-cashflow-mcp-server.c-92c0b83.kyma.ondemand.com |
| Proxy Type | Internet |
| Authentication | NoAuthentication |

The URL must NOT end with `/mcp`. Joule Studio appends that suffix
automatically when invoking the MCP server.

## Additional Properties (required for Joule visibility)

Click "New Property" for each of these. All three are required —
without them the destination will not appear in Joule Studio's
Add MCP Server dropdown.

| Key | Value |
|---|---|
| sap-joule-studio-mcp-server | true |
| sap.processautomation.enabled | true |
| sap.applicationdevelopment.actions.enabled | true |

## Verification

After saving:

1. In BTP Cockpit, click "Check Connection" on the destination — should
   return HTTP 405 (Method Not Allowed). 405 is correct here; the FastMCP
   server only accepts POST on /mcp, not the GET that the connection check
   sends. Anything other than 405 (404, 503, timeout) means the Kyma
   deployment is not reachable.

2. In Joule Studio, open or create a project, add a Joule Agent, navigate
   to the MCP Servers section, click Add MCP Server. The destination
   sap-mcp-cashflow should appear in the dropdown. If it doesn't, the
   most likely cause is a missing or misspelled additional property
   (Joule looks for the exact key `sap-joule-studio-mcp-server`).
