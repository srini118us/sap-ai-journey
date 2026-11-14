# Lab 4: add a rate-limit policy (gateway throttling)

This lab adds a Quota policy to the `GetPOStatusAPI` proxy so the gateway throttles excessive calls, then proves it by hammering the endpoint and watching the extras get rejected with HTTP 429. This is the "Rate limit" box in the MCP Gateway picture.

Builds on Lab 2 (the deployed managed API) and Lab 3 (the MCP server in front of it).

Runs on the SAP Integration Suite trial, Singapore region.

---

## 1. Why rate limiting

A gateway protects backends from abuse and overload. Without a limit, one runaway AI agent in a loop could flood the iFlow and, in a real landscape, the S/4HANA system behind it. Rate limiting is a core governance feature, and in system-design terms it is **backpressure**: the gateway refuses excess load early, at a cheap layer, instead of letting it reach and crush an expensive backend.

Two flavors:
- **Spike Arrest**: smooths bursts, caps requests per second or minute. Protects against sudden spikes. (An Apigee-style policy, part of Classic API Management.)
- **Quota**: a total allowance over a period, say 5 per minute or 1000 per day. A business or fairness limit. (Available on the Integration Cell runtime, which is what this tenant uses.)

This lab uses **Quota**, set low, so it is easy to trigger from the terminal.

---

## 2. Find the policy

Open `GetPOStatusAPI`, Edit, the **Policies** tab (the Integration Cell policy model, the adapter-style flow from Lab 2).

First gotcha: searching the **Search and Add a Step** box for `spike` or `rate` returns nothing. The Integration Cell policy model reuses the iFlow palette (Participant, Process, Event), so Apigee names like Spike Arrest are not there.

Searching `quota` does find it, under **Traffic Management, Quota**.

Second gotcha: clicking the `+` on Quota did nothing, because a step needs an **insertion point** selected first. Click the connector line between **Authorization 1** and **Request Reply** (so the quota counts only authenticated calls), then add Quota. It drops onto the flow.

---

## 3. Configure the Quota

Select the Quota step, open **Policy Settings**:

- **On Error**: **Abort** (reject calls over the limit)
- **Mode**: **Calendar**
- **Start time (UTC)**: a time already in the past, so the window is active now
- **Calls**: `5`
- **Duration**: `1`
- **Duration Unit**: **Minutes**
- **Quota Identifier**: `${context.authn.getClientID()}` (counts per client; with one calling client, all calls count together)

That means 5 calls per minute pass; the 6th is rejected. **Save** and **Deploy** the API.

The deployment status is the line under the API name: `Status: Deployed on ..., Runtime Status: STARTED`.

---

## 4. Test it

Run a loop of 7 calls in PowerShell. The `${i}` delimiting matters: `$i:` would be read as a drive reference and error.

```powershell
for ($i=1; $i -le 7; $i++) {
  Write-Host "Call ${i}:" -NoNewline
  curl.exe -s -o NUL -w " HTTP %{http_code}`n" -X POST 'https://ec8c82aetrial-04193958a9d247e7bdd3e1dfbb64d9ee.a.integration.cloud.sap/procurement' -H "Authorization: Bearer $tok"
}
```

### First run: all 401 (the token had expired)

```text
Call 1: HTTP 401
Call 2: HTTP 401
...
Call 6: HTTP 401
```

All 401 meant the token had expired (see the token note below). Refresh it:

```powershell
$tok = (curl.exe -s -X POST $turl -d 'grant_type=client_credentials' -u "${cid}:${csec}" | ConvertFrom-Json).access_token
$tok.Length
# 2046
```

### Second run: the quota kicks in

```text
Call 1: HTTP 200
Call 2: HTTP 200
Call 3: HTTP 200
Call 4: HTTP 200
Call 5: HTTP 200
Call 6: HTTP 429
Call 7: HTTP 429
```

Five calls pass, the 6th and 7th get **HTTP 429 (Too Many Requests)**. The gateway is throttling. Rate limiting proven.

---

## 5. About the token (important, applies to every lab)

The OAuth access token is **short-lived**. From `cpi-caller` it lives **one hour** (3600 seconds).

- The token is a JWT; its lifetime is `exp - iat` (expiry minus issued-at). A captured token showed `exp - iat = 3600`.
- To check it: decode the token (paste the middle segment at jwt.io) and read `exp` and `iat`; the gap is the lifetime in seconds.
- The lifetime is configurable on the XSUAA service instance (`token-validity`); one hour is the common default.

**The rule for these labs**: if a call suddenly returns **401**, the token expired, refresh it and retry. Nothing is broken.

```powershell
$tok = (curl.exe -s -X POST $turl -d 'grant_type=client_credentials' -u "${cid}:${csec}" | ConvertFrom-Json).access_token
$tok.Length   # a big number means good; 0 means set $turl/$cid/$csec again first
```

In real use you never refresh by hand: the calling app or MCP client fetches a fresh token automatically before each call or when it expires. The one-hour window is invisible to the end user.

---

## 6. In production, and where this is heading

This lab set one flat quota (5 per minute, counted across all callers) on a trial, just to see throttling work. A production landscape uses rate limiting as a real control plane:

- **Per-consumer quotas**: the `${context.authn.getClientID()}` identifier means each registered app or agent gets its own counter. In production every consumer has its own OAuth client, so one noisy agent cannot starve the others.
- **Tiered plans**: quotas become part of an API **Product** (Bronze 1k/day, Silver 10k/day, Gold unlimited), enforced per subscription. This is how API monetization and SLAs work.
- **Quota plus Spike Arrest together**: Quota caps the total over a period (fairness, cost); Spike Arrest smooths bursts per second (backend protection). Production APIs usually run both.
- **Protecting the real backend**: the point is not the gateway, it is the S/4HANA or database behind it. A quota at the gateway stops an agent loop before it ever reaches, and overloads, the ERP.
- **Alerting and analytics**: production watches consumers approaching their limits and the 429 rate, through the Analyze views or an external monitor, and alerts before a limit becomes a user-facing problem.
- **The AI-agent angle**: as more AI agents call SAP tools, per-agent quotas become a safety mechanism, a misbehaving or compromised agent is bounded by its quota, not free to hammer the ERP. This is exactly why the "agent gateway" pattern (SAP Enterprise AI Gateway, announced at TechEd 2026) puts rate limiting at the front door.

The future shape: an enterprise runs one governed gateway where every AI agent has a registered identity, a scoped set of tools, and a per-agent quota, and the platform team watches it all from one place. This lab is the smallest working piece of that picture.

---

## 7. Where this sits in the track

- Lab 0: enabling Integration Suite.
- Lab 1: first iFlow.
- Lab 2: managed API, OAuth both ways.
- Lab 3: MCP Server, the capstone.
- **Lab 4: rate-limit (Quota) policy (this lab).**
- Next: the dynamic version (a `poNumber` input, a real lookup, a live agent), plus Developer Hub publish and payload-protection, from the main track list.
