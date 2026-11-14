# Lab 2: wrap the iFlow as a managed API (with OAuth both ways)

This lab puts an API Management proxy in front of the Lab 1 iFlow. The proxy becomes the governed front door: callers authenticate to the proxy, and the proxy authenticates to the iFlow with its own stored credentials, so callers never see the backend secret. It runs on the Integration Cell runtime, the same runtime the MCP Gateway needs in Lab 3.

Builds on Lab 1 (the deployed `GetPOStatus` iFlow) and Lab 0 (the enabled tenant).

Runs on the SAP Integration Suite trial, Singapore region.

---

## 1. Why a managed API

The iFlow from Lab 1 is already callable, so why add a proxy in front of it?

Because a raw runtime endpoint is not something to hand to consumers. A managed API adds a layer that owns the cross-cutting concerns: a stable public URL, authentication, rate limits, quotas, analytics, and the ability to swap the backend without changing the caller. In system design terms it is a **gateway**: one controlled entry point in front of many services, where policy lives.

The key idea proven in this lab is **two separate security layers**:

- **Inbound**: the caller authenticates to the proxy.
- **Backend**: the proxy authenticates to the iFlow, with credentials the caller never sees.

That separation is the whole reason a managed API exists. An AI agent (Lab 3) will hold only the inbound credential and never touch the backend secret.

---

## 2. Prerequisite: activate the Integration Cell runtime

API proxies run on a runtime. In this tenant two are offered, Integration Cell (modern, cloud) and Classic API Management. The MCP Gateway in Lab 3 requires **Integration Cell**, so activate that one.

Settings, Runtimes, Integration Cell tab, **Activate**. It provisions in a few minutes, then shows Active.

A fresh login after activation brings in the **Analyze** menu and lets API artifacts be created. Note that the iFlow from Lab 1 runs on the separate Cloud Integration runtime, so it is unaffected.

---

## 3. Create the API proxy

API proxies are added inside an integration package, as an artifact, the same place as the iFlow. The Add menu in the `Procurement Integration` package now lists **API**, and at the very top, **MCP Server** (the Lab 3 artifact, confirming the whole plan works on this trial).

Choose **API**, then walk the wizard:

1. **Runtime Profile**: **Integration Cell** (not Cloud Integration; the profile decides the artifact type, and Integration Cell produces the API Management proxy the MCP server builds on).

2. **Method**: **URL or Specification** (point the API at a target URL).

3. **API Details**:
   - Name `GetPOStatusAPI`
   - URL (the backend target): the iFlow endpoint `https://ec8c82aetrial.it-cpitrial03-rt.cfapps.ap21.hana.ondemand.com/http/getpostatus`
   - Service Type **REST**
   - API Base Path `/procurement`
   - Runtime Profile **Integration Cell**

Add and open the API Designer. The proxy's public URL is:

```
https://ec8c82aetrial-04193958a9d247e7bdd3e1dfbb64d9ee.a.integration.cloud.sap/procurement
```

The **Target EndPoint** tab confirms the backend points at the iFlow:

Deploy it (Integration Cell), and wait for **Deployed / STARTED**.

---

## 4. The first failure: backend 401

Calling the proxy with the Lab 1 OAuth token:

```powershell
curl.exe -X POST 'https://ec8c82aetrial-04193958a9d247e7bdd3e1dfbb64d9ee.a.integration.cloud.sap/procurement' -H "Authorization: Bearer $tok"
An internal server error occured: The MPL ID for the failed message is : iv_qKx8SKLMJZ3mZWIXFsQ
```

The MPL ID starts with `iv_`, which is an **Integration Cell** log, not a Cloud Integration one. So the Cloud Integration monitor showed nothing, and the failure was in the proxy. Switching the monitor's **Runtime** dropdown to **Integration Cell** found the real error:

```
com.sap.it.rt.adapter.http.api.exception.HttpResponseException: An internal server error occured: HTTP operation failed invoking .../http/getpostatus with statusCode: 401
```

**Root cause**: by default a managed API proxy does not forward the caller's Authorization header to the backend (it does not leak client credentials downstream). So the iFlow received no token and returned 401. This is the core managed-API lesson: inbound and backend auth are separate, and the backend auth has to be configured on the proxy.

---

## 5. The fix: OAuth on the backend adapter

The Integration Cell policy model is adapter-based, like an iFlow. The **Request Reply** step calls the **Target** over an **HTTP** adapter, and that adapter has built-in authentication.

On the HTTP adapter (the line to Target), Connection tab, set **Authentication** to **OAuth2 Client Credentials** and give it a **Credential Name** that points to a stored credential.

The credential name references a **Security Material**, SAP's encrypted credential store. This is the clean managed pattern: the secret lives in the store, the proxy references it by name, and it never appears in the policy or the caller.

Create the material: Monitor, Manage Security, Security Material, **Create**, **OAuth2 Client Credentials**.

Fill the form to match the token request that worked in Lab 1 (Basic auth header, form-encoded body):

- **Name** `cpi-oauth-cred` (must match the adapter's Credential Name exactly)
- **Grant Type** Send as Part of Body
- **Client Authentication** Send as Request Header
- **Content Type** application/x-www-form-urlencoded
- **Token Service URL** `https://ec8c82aetrial.authentication.ap21.hana.ondemand.com/oauth/token`
- **Client ID** and **Client Secret** from the `cpi-caller-key` service key (reused from Lab 1)

Deploy the material.

Then redeploy the API so it picks up the credential.

---

## 6. The second layer: inbound security

After the backend fix, calling the proxy with **no** header returned:

```json
{"error":{"code":"noCredentials","message":"Credentials are not present"}}
```

This is a better error: the backend 401 is gone, and now the **proxy's own inbound security** is rejecting the call. The policy model has an **Authentication** and an **Authorization** step before Request Reply. The Authentication policy's type is **OAuth** (or Client Certificate).

So the proxy wants a token on the way in, and it does not forward it to the backend (the backend uses `cpi-oauth-cred`). Calling again **with** the Bearer token got past inbound auth and surfaced the next error.

---

## 7. The third failure: the token-fetch typo

With the token supplied inbound, a fresh backend failure:

```
com.sap.it.rt.adapter.http.api.exception.HttpResponseException: An internal server error occured: Exception occured while fetching OAuth Token. Reason: null
```

So inbound passed, and the proxy was now failing to fetch its own backend token via `cpi-oauth-cred`. The vague "Reason: null" turned out to be a **typo in the Token Service URL**: `tpps://` instead of `https://` (a missing `h`), entered by hand into the security material. Fixing the URL and redeploying the material cleared it.

Lesson: a vague "null" on an OAuth token fetch is almost always a bad field in the credential, the URL or the secret, not a deep platform problem.

---

## 8. Success: full end to end

The variables `$turl`, `$cid`, `$csec` are the same ones set in Lab 1 (from the `cpi-caller-key` service key). If this is a fresh terminal, set them again first:

```powershell
$turl = 'https://ec8c82aetrial.authentication.ap21.hana.ondemand.com/oauth/token'
$cid  = '<CLIENT_ID from cpi-caller-key>'
$csec = '<CLIENT_SECRET from cpi-caller-key>'
```

### The actual terminal session, start to finish

What the PowerShell window looked like across the three failures and the fix:

```text
# 1) first call to the proxy -> the iFlow backend failed (proxy did not pass auth downstream)
PS C:\Users\nivas\repos\sap-ai-journey\sap-ai-journey> curl.exe -X POST 'https://ec8c82aetrial-04193958a9d247e7bdd3e1dfbb64d9ee.a.integration.cloud.sap/procurement' -H "Authorization: Bearer $tok"
An internal server error occured: The MPL ID for the failed message is : iv_qKx8SKLMJZ3mZWIXFsQ
# (Monitor, Runtime = Integration Cell showed: HTTP operation failed invoking .../http/getpostatus with statusCode: 401)

# 2) after setting OAuth2 Client Credentials (cpi-oauth-cred) on the backend adapter, calling with NO header
PS C:\Users\nivas\repos\sap-ai-journey\sap-ai-journey> curl.exe -X POST 'https://ec8c82aetrial-04193958a9d247e7bdd3e1dfbb64d9ee.a.integration.cloud.sap/procurement'
{"error":{"code":"noCredentials","message":"Credentials are not present"}}

# 3) calling WITH the inbound token -> backend token fetch failed (typo tpps:// in the security material URL)
PS C:\Users\nivas\repos\sap-ai-journey\sap-ai-journey> curl.exe -X POST 'https://ec8c82aetrial-04193958a9d247e7bdd3e1dfbb64d9ee.a.integration.cloud.sap/procurement' -H "Authorization: Bearer $tok"
An internal server error occured: The MPL ID for the failed message is : 9BQOmNexuBIzxKY0rsI9gA
# (Monitor, Runtime = Integration Cell showed: Exception occured while fetching OAuth Token. Reason: null)

# 4) after fixing the token URL (https, not tpps) and redeploying the security material -> success
PS C:\Users\nivas\repos\sap-ai-journey\sap-ai-journey> $tok = (curl.exe -s -X POST $turl -d 'grant_type=client_credentials' -u "${cid}:${csec}" | ConvertFrom-Json).access_token
PS C:\Users\nivas\repos\sap-ai-journey\sap-ai-journey> curl.exe -X POST 'https://ec8c82aetrial-04193958a9d247e7bdd3e1dfbb64d9ee.a.integration.cloud.sap/procurement' -H "Authorization: Bearer $tok"
{
  "poNumber": "PO-1001",
  "status": "Approved",
  "amount": 15000,
  "currency": "USD",
  "supplierName": "Acme Industrial"
}
```

The JSON came back through the governed door, with both security layers working. Each failure was a layer announcing itself: the backend 401 (no backend auth), then `noCredentials` (inbound security active), then the token-fetch typo (bad field in the stored credential).

---

## 9. What the architecture looks like now

Reading the full chain:

1. The caller presents an **OAuth token to the proxy** (inbound). The Authentication policy validates it.
2. The proxy, on its own, fetches a **backend token** from XSUAA using `cpi-oauth-cred` (stored, encrypted).
3. The proxy calls the **iFlow** with that backend token. The iFlow checks the `ESBMessaging.send` role and runs.
4. The iFlow returns the JSON, back through the proxy to the caller.

Two independent tokens, two independent trust relationships. The caller never holds the backend secret, and the backend never sees the caller. That is a managed API.

---

## 10. Debugging notes worth keeping

- **`iv_` MPL IDs are Integration Cell**, not Cloud Integration. Switch the monitor's Runtime dropdown to Integration Cell to see proxy failures. Cloud Integration will show nothing.
- **A proxy does not forward the caller's Authorization header to the backend** by default. Backend auth is configured separately, on the target adapter.
- **Store backend credentials in Security Material**, referenced by name. Never in the policy, never in the caller.
- **"Exception occured while fetching OAuth Token. Reason: null"** is almost always a bad field in the credential: a typo in the Token Service URL (the `tpps` here) or the client secret.
- **Match the token request to what worked in curl**: Basic auth header, `grant_type` in the body, `application/x-www-form-urlencoded`.

---

## 11. In production, and the future

The two-layer OAuth pattern is already the production shape. What changes is the rigor around it.

- **Backend credentials are managed and rotated.** Not a reused trial service key, but a dedicated technical client with least-privilege scopes, rotated on a schedule, stored only in the Security Material or a central credential store, never in a policy or a caller.
- **Inbound auth is the enterprise IdP** (IAS, Azure AD), with scoped access, and for sensitive APIs, mutual TLS on top of the token.
- **The API is one of many** behind a shared API Management, with auth, rate limit, payload protection and CORS applied as consistent policy templates, not hand-set per API.
- **Monitored and alerted**: latency, error rate, and 4xx/5xx feed an ops dashboard, and on-call is paged before consumers notice.

The future shape: the API is published as a **Product** with plans and SLAs, and the gateway is the single audited door for both human and agent consumers. The clean 401 debugged here is the whole point, caller-side and backend-side security stay separate, forever.

---

## 12. Where this sits in the track

- Lab 0: enabling Integration Suite.
- Lab 1: first iFlow, deployed and called.
- **Lab 2: managed API with OAuth both ways (this lab).**
- Lab 3: expose this proxy as an **MCP Server**, so an AI agent can call it holding only the inbound credential.

The proxy built here is the exact thing the MCP server wraps. The agent will authenticate to the proxy inbound, and the proxy keeps handling the backend with `cpi-oauth-cred`, so the agent never touches the iFlow's security.
