# SAP Integration Suite as an MCP Gateway, lab track

The running list for the Integration Suite MCP track in the `sap-ai-journey` repo (`integration-suite/` folder). What is built, and what is worth adding next. Started from zero prior exposure to Integration Suite.

The pattern: Integration Suite becomes one governed entry point (an MCP Gateway) between AI agents and every tool they call, SAP APIs, non-SAP APIs, integration flows, data sources, and even other MCP servers. The gateway owns authentication, authorization, rate limiting, payload protection, and monitoring, so an agent holds only one inbound credential and never touches the backends.

---

## Done

- **Lab 0, Enable Integration Suite** (trial): Singapore region requirement, entitlements, capability activation, PI roles plus a fresh login. Gets the Design and Monitor menus to appear.
- **Lab 1, First iFlow**: an HTTPS request-reply flow that returns JSON, deployed on Cloud Integration, called over OAuth.
- **Lab 2, Managed API**: an API Management proxy in front of the iFlow, with OAuth both ways, inbound token validation and a backend OAuth2 Client Credentials security material. Two independent security layers.
- **Lab 3, MCP Server**: the API exposed as an MCP tool, called from the MCP Inspector, live JSON back through the full chain. The capstone.
- **Lab 4, Rate-limit (Quota) policy**: a Quota on the API proxy (5 calls per minute), proven with a curl loop, 5 pass then HTTP 429. The gateway's throttling layer.

Every lab doc now also carries an **"In production, and the future"** section (how the step looks in a real landscape) and a shared **token note** (the OAuth token lives one hour; a 401 means refresh it).

Chain proven end to end:
```
AI agent (MCP client)
  -> MCP Server (inbound OAuth)
  -> API Management proxy (fetches its own backend token)
  -> iFlow (role-checked)
  -> JSON, back up the chain
```

---

## Planned next, the valuable add-ons

**Lab 5, make it dynamic and agent-driven** (the big one)
- Add a `poNumber` input to the tool.
- Have the iFlow use it to look up real data (S/4HANA via OData, a CAP service, or a small lookup table to start) instead of returning a constant.
- Connect a real MCP client (Claude Desktop or SAP Joule) and ask in plain English, "Is PO-1003 approved?"
- Turns the secure highway into something that answers real questions.

**Publish to Developer Hub** (step 4 of the community checklist, skipped so far)
- Package the API as a Product and publish it in the Developer Hub so agents and developers can discover and subscribe to it. Not required for the server to run, but completes the governed-catalog story.

**Add gateway policies** (the remaining boxes in the MCP Gateway diagram)
- **Rate limit** (Quota): done in Lab 4. Per-consumer and tiered quotas are the production extension.
- **Payload protection**: validate and bound request and response bodies.
- **Monitoring**: use the Analyze views to watch calls, latency, and errors per tool.

**Widen what the gateway fronts** (same MCP server pattern, different sources)
- Non-SAP APIs, data sources, and even external MCP servers, all behind the one governed door.

---

## Reference and context

- Matches the SAP community "Integration Suite is now an MCP Gateway" pattern (Kader Kara, SAP Technical Architect, Nov 2026) and the SAP Developer Center tutorial "Build and Govern MCP Servers with SAP Integration Suite" (Oct 2026).
- The MCP Gateway shipped in 2026 and runs on the **Integration Cell** runtime.
- **Trial is fine for learning. Productive use needs SAP Integration Suite Premium or Enhanced Edition** (SAP Note 2903776). Same region fine print from Lab 0: Singapore (ap21) supported, some regions gated.
- **SAP TechEd 2026**: the agent gateway is generally available, and SAP announced the **SAP Enterprise AI Gateway**, built on SAP Integration Suite.

---

## How this maps to the CAP MCP labs

This track is the SAP-native gateway version of the CAP MCP labs already in the repo. CAP exposed MCP through the `@cap-js/mcp` plugin (an app being its own MCP server). Integration Suite exposes MCP natively through the gateway (no plugin), fronting any backend with full governance. Two valid patterns, same goal: an AI agent reaching live SAP data safely.
