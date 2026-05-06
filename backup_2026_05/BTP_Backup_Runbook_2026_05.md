# SAP BTP Backup Runbook — May 2026

**Backup target directory:** `C:\Users\nivas\repos\sap-ai-journey\backup_2026_05\` (WSL: `/mnt/c/Users/nivas/repos/sap-ai-journey/backup_2026_05/`)
**Encrypted secrets file:** `sap_btp_secrets_2026_05.7z` (AES 256, password in 1Password)
**Subaccount:** sap-btp-joule (us10) | **CF org:** org-build-sap-btp-joule | **Space:** build
**Planning deadline:** May 16, 2026 (conservative; pending admin confirmation)
**Author:** Srinivasa | **Started:** May 3, 2026

---

## Deadline framing

Two scenarios, same backup work, different pacing:

| Admin response | Effective deadline | Pacing |
|---|---|---|
| Hard delete on expiry | May 16 (conservative) | Steps 0 to 7 across 2 to 3 sessions, finish by May 13 |
| Soft suspension with retention (e.g., 30 days) | mid-June | Same steps, pace relaxed; verification pass can extend |

If admin confirms soft suspension, update this header and slow the schedule. Do not skip steps; soft suspension only buys time, it does not eliminate risk (rental admin can change policy without notice).

---

## Step 0. Confirm rental expiry policy

Status: [ ] Sent [ ] Replied

**Action:** Email rental admin with the following two questions.

```
1. What is the exact expiry date for the sap-btp-joule rental?
2. On expiry, is the subaccount hard deleted immediately, or soft suspended with a retention window? If retention, how many days?
```

**Verified by:** _Admin reply pasted here, dated._

**Decision after reply:**
- If hard delete: proceed with May 16 schedule.
- If soft suspension: update deadline above, proceed at relaxed pace.

---

## Step 1. Inventory pass (read only, no exports)

Goal: enumerate every artifact on the tenant before we touch anything. Output is a single text file we use to scope Steps 2 through 7.

Status: [ ] Run [ ] Output reviewed [ ] Scope locked

**How to run:**

1. Open WSL terminal.
2. `cd /mnt/c/Users/nivas/repos/sap-ai-journey/backup_2026_05/`
3. Save the `inventory_pass.sh` script (provided alongside this runbook) into this directory.
4. `chmod +x inventory_pass.sh`
5. Make sure you are logged into CF: `cf login -a https://api.cf.us10-001.hana.ondemand.com` (use email and password, not SSO; org `org-build-sap-btp-joule`, space `build`).
6. `./inventory_pass.sh`
7. Review `inventory_output.txt`.

**What the script captures:**

| Category | Method | Notes |
|---|---|---|
| CF apps | `cf apps` | All deployed apps in space `build` |
| CF services | `cf services` | All bound service instances |
| CF service keys (names only, no values) | `cf service-keys <name>` per service | Just the names, so we know what to export later |
| BTP destinations (cockpit) | Manual list (cockpit does not expose CLI for trial dest service) | Capture screenshot to `inventory_destinations.png` |
| SBPA projects | Manual via SBPA Lobby | List project names and last modified dates to `inventory_sbpa.txt` |
| Joule agents and skills | Manual via Joule Studio | List to `inventory_joule.txt` |
| AI Core resource groups, scenarios, configurations, deployments | `aicore` btp CLI plugin or curl against AI API | See script for endpoint list |
| AI Core object store secrets, generic secrets, datasets | curl against AI API metadata endpoints | Names only, no contents |
| HANA Cloud instances | `cf services` filter | Plus cockpit screenshot for state and size |
| GitHub remote status | `git status && git log origin/master..HEAD` | In `srini118us/sap-ai-journey` working copy |
| Docker Hub local images | `docker images \| grep srini117us` | And note which are pushed |

**Verified by:** _Paste a one paragraph summary of the inventory_output.txt findings here. Item count per category, any surprises._

**Stop here. Do not proceed to Step 2 until the inventory output has been reviewed and the scope is locked.**

---

## Step 2. SBPA project exports (.mtar)

Status: [ ] Not started

Scope to be filled from Step 1 output. Known so far:

| Project | Status | Destination | Verified by |
|---|---|---|---|
| UC2.8-SAP-Native-Treasury | Done May 3 | `backup_2026_05/sbpa/UC2.8-SAP-Native-Treasury.mtar` | (Confirm SHA256 still matches original export) |
| _Lab A procurement (?)_ | Pending Step 1 | _TBD_ | _TBD_ |
| _Other (?)_ | Pending Step 1 | _TBD_ | _TBD_ |

To be expanded after Step 1.

---

## Step 3. BTP destinations export (JSON)

Status: [ ] Not started

Known destinations (from prior session memory; verify in Step 1):

| Destination | Used by | Exported | Verified by |
|---|---|---|---|
| IntegrationSuite | UC2.8 | [ ] | _TBD_ |
| sap-mcp-cashflow | UC2.7 | [ ] | _TBD_ |
| _Other (?)_ | Pending Step 1 | [ ] | _TBD_ |

To be expanded after Step 1.

---

## Step 4. Service keys export (encrypted, separate)

Status: [ ] Not started

**Critical:** Service keys do NOT go in the regular backup directory. They go into `sap_btp_secrets_2026_05.7z` only. Workflow:

1. `cf service-key <service> <key-name> > /tmp/key.json`
2. Append to a single staging directory: `/tmp/btp_keys_staging/`
3. After all keys collected, compress with 7-Zip AES 256:
   ```
   "C:\Program Files\7-Zip\7z.exe" a -p -mhe=on sap_btp_secrets_2026_05.7z C:\Users\nivas\AppData\Local\Temp\btp_keys_staging\
   ```
   The `-p` prompt enters the password (do not put it on the command line). `-mhe=on` encrypts headers so filenames are also hidden.
4. Verify the .7z extracts with the password.
5. Shred the staging directory.
6. Store the password in 1Password under entry "SAP BTP backup 2026-05".

| Service | Key name | Staged | Encrypted | Verified by |
|---|---|---|---|---|
| AI Core (ai-launchpad) | _TBD_ | [ ] | [ ] | _TBD_ |
| AI Core (ml-training) | _TBD_ | [ ] | [ ] | _TBD_ |
| HANA Cloud | _TBD_ | [ ] | [ ] | _TBD_ |
| SBPA runtime | _TBD_ | [ ] | [ ] | _TBD_ |
| Joule | _TBD_ | [ ] | [ ] | _TBD_ |
| _Other (?)_ | _TBD_ | [ ] | [ ] | _TBD_ |

---

## Step 5. Joule configs export

Status: [ ] Not started

Known agents and skills (from prior session memory; verify in Step 1):

| Artifact | Type | Source | Exported | Verified by |
|---|---|---|---|---|
| cashflow-forecast-agent | Agent | UC2.7 | [ ] | _TBD_ |
| _Lab A procurement skills (?)_ | Skill | Pending Step 1 | [ ] | _TBD_ |
| _Lab A procurement agent (?)_ | Agent | Pending Step 1 | [ ] | _TBD_ |

Joule export method: agents and skills export as JSON via Joule Studio "Download" action per artifact. To be expanded after Step 1.

---

## Step 6. AI Core artifacts export

Status: [ ] Not started

Cross resource group complexity (flagged in your context): UC2.6 explainer is in `ml-training`, GPT 4o and orchestration are in `ai-launchpad`, scenarios may be shared. Inventory must capture which RG each artifact lives in.

| Artifact | RG | Type | Exported | Verified by |
|---|---|---|---|---|
| Deployment d00c85f445274f70 | _TBD_ | Explainer | [ ] | _TBD_ |
| Deployment d50ff74c | _TBD_ | Per company | [ ] | _TBD_ |
| Deployment d8ecefa3 | _TBD_ | Per company | [ ] | _TBD_ |
| Deployment db182... (orchestration) | _TBD_ | Orchestration | [ ] | _TBD_ |
| Object Store Secret | _TBD_ | Secret | [ ] | _TBD_ |
| Generic Secret | _TBD_ | Secret | [ ] | _TBD_ |
| Datasets | _TBD_ | Data | [ ] | _TBD_ |
| Configurations | _TBD_ | Config | [ ] | _TBD_ |
| SHAP artifacts in S3 | _TBD_ | Artifact | [ ] | _TBD_ |

To be expanded after Step 1. Export method per artifact type to be added once inventory confirms exact endpoints (AI API metadata pull, S3 sync for object store contents).

---

## Step 7. Verify GitHub and Docker Hub remotes are current

Status: [ ] Not started

| Check | Command | Expected | Verified by |
|---|---|---|---|
| Local working copy clean | `cd ~/repos/sap-ai-journey && git status` | "nothing to commit, working tree clean" | _TBD_ |
| Local ahead of remote | `git log origin/master..HEAD --oneline` | empty (or pushed) | _TBD_ |
| Docker images present | `docker images \| grep srini117us` | All UC images listed | _TBD_ |
| Docker images pushed | `docker manifest inspect srini117us/<image>:<tag>` per image | Manifest returned (pushed) | _TBD_ |

---

## Step 8. Recovery procedure (fresh tenant restore)

Status: [ ] Drafted [ ] Tested

Written after Steps 1 through 7 are complete. Skeleton:

1. Provision fresh BTP subaccount and CF space.
2. Recreate destinations from JSON files in `backup_2026_05/destinations/`.
3. Provision service instances per `inventory_output.txt` service list.
4. Restore service keys from encrypted .7z (1Password password) and re-bind.
5. Deploy SBPA .mtar files via SBPA Lobby.
6. Re-import Joule agents and skills.
7. Recreate AI Core resource groups, scenarios, configurations, deployments per AI Core inventory.
8. Re-link orchestration scenarios across RGs.
9. Smoke test each UC.

To be completed after Step 1 inventory locks the actual artifact list.

---

## Session log

| Date | Session goal | Steps completed | Outstanding |
|---|---|---|---|
| 2026-05-03 | Runbook scaffold + Step 0/1 prep | Runbook drafted, inventory script ready | Send Step 0 email, run Step 1 |
| _TBD_ | Step 1 review + Step 2/3 exports | _TBD_ | _TBD_ |
| _TBD_ | Step 4/5/6 exports | _TBD_ | _TBD_ |
| _TBD_ | Step 7 verification + Step 8 recovery doc | _TBD_ | _TBD_ |
