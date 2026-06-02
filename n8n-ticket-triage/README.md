# Support Ticket Triage with n8n + Claude + Data Tables

A working AI triage pipeline built end to end on a local self hosted n8n instance. This document records the purpose, architecture, every build step as actually done, and the gotchas encountered, with space after each step to paste a screenshot.

Built: June 2026
Environment: n8n 2.22.6 self hosted (npx, Windows, Node 24), Claude API, native n8n Data Tables
Author: Srinivasa

---

## 1. Purpose

Incoming support tickets arrive as unstructured free text. A human normally reads each one and decides what it is about, how urgent it is, and which team should handle it. This workflow automates that triage step. Claude reads each ticket and assigns three things: a category, a priority, and the owning team. The results are written back to a table so the queue is always sorted and routed without manual effort.

This is deliberately more than field extraction. Extraction pulls values that already sit in the text. Triage requires judgment: the words "charged twice and need a refund" never say "Billing" or "Finance", yet the ticket must route there. Claude makes that decision, which is what makes this an agentic flavored task rather than a parser.

Why this matters as a pattern: any queue of unstructured items that needs classifying and routing (tickets, leads, emails, documents) follows this exact shape. The ticket case is a clean, recognizable instance of it.

---

## 2. Architecture

Five nodes in a linear chain, no branches, no external dependencies beyond the Claude API.

```
Manual Trigger
      |
      v
Data Table: Get row(s)        read tickets where status = NEW
      |
      v
HTTP Request: Claude          classify each ticket (runs once per item)
      |
      v
Code (JavaScript)             parse Claude JSON, re-attach ticketid
      |
      v
Data Table: Upsert row(s)     write category/priority/team, flip status to TRIAGED
```

Data store: a single native n8n Data Table named `tickets` with columns ticketid, customer, message, status, category, priority, team. Status is the control column: NEW means needs triage, TRIAGED means done.

Key design properties:
- Self contained. The Data Table lives inside n8n. No Google, no OAuth, no external database, no local files. The Claude API is the only outside call.
- Item fan out. Get row(s) emits one item per matching ticket, so the HTTP, Code, and Upsert nodes each run once per ticket automatically. No explicit loop node needed.
- Idempotent by design. The Get filter only pulls status = NEW, and the Upsert flips status to TRIAGED. Re-running never reprocesses a ticket that is already done. This is the same principle as a job queue with a claimed flag, and it is what makes the workflow safe to put on a schedule.
- Constrained classification. Claude is told to return only one of a fixed set for each field (category, priority, team). Constraining the output set is what makes the result reliable and routable rather than free text that downstream nodes cannot act on.

---

## 3. Prerequisites

- n8n running locally. Started with `npx n8n` from a non system folder, on Node 24 (n8n 2.22 requires Node 22.16 or higher; an older Node will fail the install with an EBADENGINE error).
- A Claude API key from console.anthropic.com.
- The key stored as an HTTP header named x-api-key (set on the HTTP Request node).

---

## 4. Build steps

Each step below has a space to paste the matching screenshot.

### Step 1: create the Data Table

On the n8n Overview page, open the Data tables tab. Top right split button, Create Data table. Name it `tickets`. Add seven String columns: ticketid, customer, message, status, category, priority, team. Add three sample rows with status NEW and category/priority/team left empty (Null):

- T-001, Jane Doe, "I was charged twice for my subscription this month and need a refund", NEW
- T-002, Raj Patel, "The app crashes every time I open the reports page on Android", NEW
- T-003, Mia Chen, "How do I export my data to CSV? Cannot find the option", NEW

Note: the column ended up named `ticketid` (no underscore). That exact name is referenced later in the Code node, so the names must match.

_Screenshot:_

\
\
\
\
\

### Step 2: Manual Trigger

New workflow, Create workflow. Add first step, Trigger manually. This is for testing by clicking; it gets swapped for a Schedule Trigger in production (see section 7).

_Screenshot:_

\
\
\
\
\

### Step 3: Data Table, Get row(s)

Add a Data Table node after the trigger. Under Row Actions choose Get row(s).
- Data table: tickets (From list)
- Add Condition: Column status, Equals, Value NEW

Run Execute workflow (the canvas button, not Execute step). Output should show 3 items, the three NEW tickets.

_Screenshot:_

\
\
\
\
\

### Step 4: HTTP Request, Claude classify

Add an HTTP Request node.
- Method POST
- URL https://api.anthropic.com/v1/messages
- Authentication: Generic Credential Type, Header Auth, the x-api-key credential
- Send Headers on: anthropic-version = 2023-06-01, content-type = application/json
- Send Body on, Body Content Type JSON, Specify Body Using JSON, body:

```json
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 300,
  "messages": [
    {
      "role": "user",
      "content": "You are a support ticket triage agent. Respond with strict JSON only, no prose, no markdown. Fields: category (Billing, Bug, How-To, Account, Other), priority (Low, Medium, High, Urgent), team (Finance, Engineering, Support, Success). Ticket from {{ $json.customer }}: {{ $json.message }}"
    }
  ]
}
```

The {{ $json.customer }} and {{ $json.message }} expressions pull from each ticket row. Because Get row(s) emitted 3 items, this node runs 3 times, once per ticket.

Run Execute workflow. Output is 3 items, each a Claude response containing classification JSON inside content[0].text.

_Screenshot:_

\
\
\
\
\

### Step 5: Code, parse and re-attach ticketid

Add a Code node (language JavaScript). It loops over all items, parses each Claude response, and re-attaches the original ticketid so the next node knows which row to update:

```javascript
return $input.all().map((item, i) => {
  const text = item.json.content[0].text;
  const d = JSON.parse(text.replace(/```json|```/g, '').trim());
  return {
    json: {
      ticketid: $('Get row(s)').all()[i].json.ticketid,
      category: d.category,
      priority: d.priority,
      team: d.team,
      status: 'TRIAGED'
    }
  };
});
```

Note: the first attempt used `$input.first()`, which only processed one ticket and produced 1 item out of 3 in. Switching to `$input.all().map(...)` processes every item. The `$('Get row(s)').all()[i]` reference pairs each Claude response with its source ticket by index.

Run Execute workflow. Output should be 3 items, each with ticketid, category, priority, team, and status TRIAGED. Use the Table view in the output panel to see all three at once:

- T-001, Billing, High, Finance, TRIAGED
- T-002, Bug, High, Engineering, TRIAGED
- T-003, How-To, Low, Support, TRIAGED

_Screenshot:_

\
\
\
\
\

### Step 6: Data Table, Upsert row(s)

Add a final Data Table node, Upsert row(s) (Upsert updates the row if the match exists, which is what we want).
- Data table: tickets
- Must Match: All Conditions
- Condition: Column ticketid, Equals, Value (expression) {{ $json.ticketid }}
- Mapping Column Mode: Map Each Column Manually
- Values to set (each in expression mode):
  - status = {{ $json.status }}
  - category = {{ $json.category }}
  - priority = {{ $json.priority }}
  - team = {{ $json.team }}
- Leave ticketid, customer, message empty so they are not overwritten.

Run Execute workflow. All five nodes go green, 3 items flow through the whole chain.

_Screenshot:_

\
\
\
\
\

### Step 7: verify the result in the table

Open Data tables, tickets. The three rows now show category, priority, team filled and status flipped to TRIAGED, written by the workflow itself:

| ticketid | customer | message | status | category | priority | team |
|---|---|---|---|---|---|---|
| T-001 | Jane Doe | charged twice, refund | TRIAGED | Billing | High | Finance |
| T-002 | Raj Patel | app crashes on Android | TRIAGED | Bug | High | Engineering |
| T-003 | Mia Chen | how to export CSV | TRIAGED | How-To | Low | Support |

_Screenshot:_

\
\
\
\
\

---

## 5. Gotchas and lessons learned

These cost time during the build and are worth recording for next time.

- Node version. n8n 2.22 requires Node 22.16 or higher. Node 20.12 failed the npx install with EBADENGINE; upgrading to Node 24 fixed it.
- Execute step vs Execute workflow. Execute step runs a single node with whatever input is cached, often stale or empty, which caused repeated "Unexpected end of JSON input" errors. Always run the whole chain with the canvas Execute workflow button so each node receives live upstream data.
- File access sandbox (only relevant if writing to disk). n8n blocks file writes unless the target folder is whitelisted with the N8N_RESTRICT_FILE_ACCESS_TO environment variable. This is why the project moved away from local CSV output entirely.
- Google OAuth. Connecting n8n to Google Sheets on localhost was repeatedly blocked (insufficient parameters, cached sessions hijacking the flow, redirect mismatches). Native Data Tables avoided all of it and are the cleaner choice for a self contained workflow anyway.
- Item count is the tell. When the Code node showed 1 item out while 3 came in, that signaled the code processed only the first item. Watching the item count on each connection is a fast way to catch fan out bugs.
- Expressions must be in expression mode. Values like {{ $json.ticketid }} only evaluate when the field is switched to expression mode (the fx toggle), otherwise they are treated as literal text.
- Column name must match exactly. The table column is ticketid (no underscore), so the Code node uses ticketid, not ticket_id. A mismatch breaks the update silently.

---

## 6. How the data flows (end to end)

1. Trigger fires.
2. Get row(s) queries the tickets table for status = NEW and emits one item per matching ticket.
3. For each item, HTTP Request sends the customer and message to Claude with a constrained classification prompt.
4. Claude returns JSON: category, priority, team.
5. The Code node parses each response and re-attaches the ticketid, adding status = TRIAGED.
6. Upsert writes category, priority, team, and status back to the matching row.
7. Re-running does nothing to already TRIAGED rows because the Get filter only matches NEW.

---

## 7. Making it production (next steps, not yet done)

- Replace the Manual Trigger with a Schedule Trigger (for example every 5 minutes), then Save and toggle the workflow Active. It will run on its own. The NEW to TRIAGED idempotency makes scheduled runs safe.
- Add an escalation branch: an IF node after the Code node testing priority = Urgent or High, routing to an alert (email, Slack) for hot tickets.
- Add error handling: wrap the Code parse in try/catch and route unparseable responses to an error path or a separate table column rather than failing the run; add a retry on the HTTP node.
- Consider batching: for large volumes, the Data Table node has an optimized bulk insert/upsert path.

---

## 8. Conclusion

_Write final thoughts here: what worked, what was learned about n8n, how this maps to a real production use case, and any ideas for extending it._

\
\
\
\
\
\
\
\
