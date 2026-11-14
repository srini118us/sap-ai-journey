# Lab 0: Enabling SAP Integration Suite on a trial (from zero)

This is the first lab in the Integration Suite track. It does not build anything yet. It gets Integration Suite from a blank trial to a working tenant where the Design and Monitor menus appear and an integration flow can be built. Written step by step, because the enablement has several traps that are easy to hit and hard to diagnose, and the error messages do not point at the real cause.

If the Design and Monitor menus are missing, or a booster keeps failing, this lab is the fix.

---

## 1. What Integration Suite is, in one picture

SAP Integration Suite is an iPaaS (integration platform as a service). It is the place where integrations and APIs live: pipelines that move and transform data between systems, and a gateway that exposes those as managed APIs. In this track it is also the host for the MCP Gateway later, which turns a managed API into a tool an AI agent can call.

The product is made of **capabilities**, each activated separately inside one tenant:

- **Cloud Integration** (Build Integration Scenarios): build and run integration flows. This is what gives the **Design** and **Monitor** menus.
- **API Management** (Manage APIs): expose and govern APIs. This is the base for the MCP Gateway.
- Others: Trading Partner Management, Integration Advisor, Open Connectors, OData Provisioning, and the two Assessments.

A capability being listed is not the same as a capability being active, and a capability being active is not the same as the user having the roles to see it. Those three things are separate, and all three must be true. That is the core lesson of this lab.

---

## 2. The mental model that avoids the pain

Three independent things must line up before the menus appear:

1. **Capability activated**: Cloud Integration and API Management turned on in the tenant.
2. **Service instance created**: a runtime service instance exists (Process Integration Runtime for Cloud Integration, API portal and developer portal for API Management). This needs **entitlements** (quota) assigned to the subaccount first.
3. **Role collections assigned**: the user holds the PI_* roles (Cloud Integration) and the API Management roles, then logs in fresh.

Miss any one and the menu stays thin (only Home and Settings). The error messages rarely say which of the three is missing, so the trick is to check all three in order.

---

## 3. The region trap (this one cost the most time)

**Finding: the SAP BTP trial automated setup for Integration Suite works smoothly only in the Singapore region (ap21).** In US East (us10) and other regions, the one-click booster refuses to run, and Cloud Integration provisioning is flaky.

This was discovered the hard way. On a US10 trial, every capability showed Active, every role was assigned, and the menu still would not show Design or Monitor. The Integration Cell runtime was active, API Management was active, roles were assigned, and nothing worked.

The booster then said it plainly:

> The Enable Integration Suite booster is supported only in the Singapore region. Select a Singapore subaccount to continue.

**Decision: switch to a Singapore (ap21) trial subaccount.** Since no integration flows existed yet, there was nothing to lose by starting fresh in the right region. Everything below is in Singapore.

Why document this: the error does not appear until deep into the setup, after a lot of clicking. Knowing it up front saves hours. **Start Integration Suite trials in Singapore.**

---

## 4. Step 1: subscribe to Integration Suite

A fresh Singapore trial subaccount had only Business Application Studio subscribed.

Subscribe to Integration Suite:

1. In the subaccount, open **Services, Service Marketplace**.
2. Search **Integration Suite**.
3. Click the tile, then **Create**, plan **trial**, **Create**.

Result: Integration Suite appears under Instances and Subscriptions as **Subscribed**, next to BAS.

---

## 5. Step 2: assign the provisioner role, then activate capabilities

Opening Integration Suite the first time needs the **Integration_Provisioner** role, or it throws an authorization error.

1. BTP Cockpit, **Security, Role Collections** (or **Users**), assign **Integration_Provisioner** to the user.
2. Open Integration Suite, **Go to Application**.
3. **Manage Capabilities, Add Capabilities**, tick **Build Integration Scenarios** (Cloud Integration) and **Design, Develop, and Manage APIs** (API Management). All capabilities can be ticked if a full playground is wanted; the two named here are the ones this track needs.
4. **Activate**. Provisioning takes a few minutes.

Note on the region fine print (SAP Note 2903776): some capabilities are not available in Alibaba Shanghai, EU Access, or Sovereign/NS2 regions. Singapore (ap21) is none of those, so every capability including the Integration Cell runtime is available.

---

## 6. Step 3: the Enable Integration Suite booster, and the entitlement trap

The booster does two jobs in one guided flow: assigns the runtime role collections, and creates the service instances. Run it from BTP Cockpit, **Boosters**, **Enable Integration Suite**, **Start**.

On the first run it failed:

> Service quotas for the below entitlements could not be assigned: SAP Process Integration Runtime, API Management API portal, API Management developer portal.

**Root cause: the subaccount had no entitlements (quota) for those service plans.** The booster cannot create a service instance for a plan the subaccount is not entitled to.

Fix: add the entitlements to the **subaccount** (not the global Service Assignments view, which trial locks and shows no edit button).

1. Subaccount, **Entitlements**, **Edit**.
2. **Add Service Plans**, add:
   - **SAP Process Integration Runtime** (technical name `it-rt`), plan **integration-flow**
   - **API Management, API portal**, plan **apiportal-apiaccess**
   - **API Management, developer portal**, plan **devportal-apiaccess**
3. **Save**.

A subtlety: in the Add Service Plans catalog, plans already entitled show pre-ticked and locked, with the Add button disabled and showing "Add 0". That is not an error. It means the plan is already there, nothing to add.

---

## 7. Step 4: the real key, the PI role collections and a fresh login

Even after the entitlements were in place, the booster kept failing on the same quota error (a trial quirk). So the booster was abandoned. It is optional. Its two jobs can be done by hand, and the one that actually reveals the menu is the roles.

**The Design and Monitor menu does not need a service instance. It needs the Cloud Integration capability (done), a PI role collection, and a fresh login.**

Assign the role collections:

- Cloud Integration: **PI_Administrator, PI_Business_Expert, PI_Integration_Developer, PI_Read_Only**
- API Management (for later): **APIManagement.SelfService.Administrator, APIPortal.Administrator, APIPortal.Developer, APIPortal.Tester, AuthGroup.API.Admin**

Then, and this is the step everyone misses, **log out of Integration Suite completely and log back in**. Roles only take effect on a fresh session. A plain page refresh does not do it; use incognito if the session is sticky.

Result: the full menu appears, Discover, Design, Modernize, Monitor, Inspect.

---

## 8. The checklist, condensed

For next time, enable Integration Suite in this order:

1. Use a **Singapore (ap21)** trial subaccount. Not US, not EU Access, not sovereign.
2. **Subscribe** to Integration Suite (Service Marketplace).
3. Assign **Integration_Provisioner**, open the app.
4. **Activate capabilities**: Cloud Integration and API Management.
5. Add **subaccount entitlements**: Process Integration Runtime (integration-flow), API Management API portal (apiportal-apiaccess), developer portal (devportal-apiaccess).
6. Run the **Enable Integration Suite booster**, or do its jobs by hand.
7. Assign the **PI_* and API role collections**.
8. **Log out and back in** (incognito if needed).

If the menu is still thin after all that, it is almost always number 8: the login was not fresh.

---

## 9. Gotchas worth remembering

- **Capability tiles on the Home page are not buttons.** Clicking Build Integration Scenarios does nothing. Navigation is the hamburger menu on the top left, or the tiles do not link at all until the menu is built.
- **The properties panel is docked at the bottom** of the iFlow editor, often collapsed. If a step's properties seem missing, expand the bottom panel.
- **Listed is not active, active is not visible.** A capability can be listed on Home, activated in the tenant, and still invisible to the user without roles and a fresh login.
- **The booster is region-locked and optional.** If it fails, do its two jobs by hand (entitlements plus service instance, and role collections).
- **PI_* roles plus a fresh login is the real unlock** for the Design and Monitor menu.

---

## 10. In production, and the future

The trial made this painful; a productive landscape is the opposite, deliberate and automated.

- **Not a trial.** Production runs a licensed Integration Suite (Premium or Enhanced Edition, per SAP Note 2903776) in a productive BTP global account, with support and SLAs, not the free tier.
- **Enablement is automated, not clicked.** Capabilities, entitlements and runtimes are provisioned with the btp CLI or Terraform, so the whole setup is repeatable and version-controlled, none of the manual role-and-login dance from this lab.
- **Roles come from the identity provider.** Users get access through IAS or Azure AD group assignments, not individual role collections, so joiners and leavers are handled by the directory.
- **Region is a data-residency decision**, chosen for where the data must live and for latency, not for which region happens to run the booster.
- **Separate subaccounts for dev, test and prod**, with content transported through CI/CD (CTS+ or gCTS), not rebuilt by hand in each.

The future shape: the SAP Enterprise AI Gateway announced at TechEd 2026 is this enablement productized, a platform team stands up the agent gateway once, governs it centrally, and teams onboard onto it. This lab is the hand-built version of that first step.

---

## 11. Where this sits in the track

This is Lab 0, the foundation. With the tenant enabled, the ladder is:

- **Lab 1**: first integration flow, build, deploy, and call it (next).
- **Lab 2**: wrap the iFlow endpoint as a managed API in API Management.
- **Lab 3**: expose that API as an MCP tool through the MCP Gateway, so an AI agent can call it.

The payoff of this painful setup is that the rest of the ladder runs on a working tenant.
