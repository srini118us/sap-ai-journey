#!/bin/bash
# inventory_pass.sh
# Read only enumeration of BTP tenant artifacts.
# Run from: /mnt/c/Users/nivas/repos/sap-ai-journey/backup_2026_05/
# Prerequisites: cf CLI logged in, btp CLI logged in (optional), curl, jq.
# Output: inventory_output.txt in current directory.

set -u
OUT="inventory_output.txt"
echo "SAP BTP Inventory Pass" > "$OUT"
echo "Generated: $(date -Iseconds)" >> "$OUT"
echo "=======================================" >> "$OUT"

section() {
  echo "" >> "$OUT"
  echo "=== $1 ===" >> "$OUT"
}

# 1. CF context
section "CF target"
cf target >> "$OUT" 2>&1 || echo "cf not logged in — fix this and re-run" >> "$OUT"

# 2. CF apps
section "CF apps"
cf apps >> "$OUT" 2>&1

# 3. CF services
section "CF services"
cf services >> "$OUT" 2>&1

# 4. Service keys per service (names only)
section "CF service keys (names only)"
cf services 2>/dev/null | tail -n +4 | awk '{print $1}' | while read svc; do
  if [ -n "$svc" ]; then
    echo "" >> "$OUT"
    echo "--- Service: $svc ---" >> "$OUT"
    cf service-keys "$svc" >> "$OUT" 2>&1 || echo "  (no keys or access denied)" >> "$OUT"
  fi
done

# 5. CF routes
section "CF routes"
cf routes >> "$OUT" 2>&1

# 6. Manual checklist (cannot script these)
section "MANUAL inventory required (script cannot enumerate)"
cat >> "$OUT" <<'EOF'
The following must be enumerated manually from the cockpit. Capture each as
a separate text file or screenshot in this directory.

a) BTP destinations
   - Cockpit: Subaccount sap-btp-joule > Connectivity > Destinations
   - Save as: inventory_destinations.png (screenshot of full list)
   - For each destination, also note: Name, Type, URL, Authentication type
     in inventory_destinations.txt

b) SBPA projects
   - SBPA Lobby > All Projects
   - Save as: inventory_sbpa.txt (one line per project: Name | Last modified | Status)

c) Joule agents and skills
   - Joule Studio > Agents tab > list all
   - Joule Studio > Skills tab > list all
   - Save as: inventory_joule.txt

d) AI Core artifacts (cross resource group)
   - AI Launchpad > Resource Groups > expand each
   - For each RG (ml-training, ai-launchpad, default, others):
     - List Scenarios, Configurations, Deployments, Datasets,
       Object Store Secrets, Generic Secrets
   - Save as: inventory_aicore.txt

e) HANA Cloud
   - Cockpit > Services > Instances and Subscriptions > HANA Cloud
   - Note: instance name, state (running/stopped), size, last activity
   - Save as: inventory_hana.txt

EOF

# 7. AI Core via API (if AICORE_AUTH_URL etc are exported)
section "AI Core via API (optional, requires env vars)"
if [ -n "${AICORE_AUTH_URL:-}" ] && [ -n "${AICORE_CLIENT_ID:-}" ] && [ -n "${AICORE_CLIENT_SECRET:-}" ] && [ -n "${AICORE_BASE_URL:-}" ]; then
  echo "Fetching AI Core token..." >> "$OUT"
  TOKEN=$(curl -s -u "$AICORE_CLIENT_ID:$AICORE_CLIENT_SECRET" \
    -d "grant_type=client_credentials" \
    "$AICORE_AUTH_URL/oauth/token" | jq -r '.access_token' 2>/dev/null)
  if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    for RG in ml-training ai-launchpad default; do
      echo "" >> "$OUT"
      echo "--- RG: $RG ---" >> "$OUT"
      for ENDPOINT in scenarios configurations deployments datasets executables; do
        echo "[$ENDPOINT]" >> "$OUT"
        curl -s -H "Authorization: Bearer $TOKEN" \
          -H "AI-Resource-Group: $RG" \
          "$AICORE_BASE_URL/v2/lm/$ENDPOINT" | jq '.resources // .count // .' >> "$OUT" 2>&1
      done
    done
  else
    echo "Could not get AI Core token. Skip and use manual cockpit inventory." >> "$OUT"
  fi
else
  echo "AI Core env vars not set. Export AICORE_AUTH_URL, AICORE_CLIENT_ID," >> "$OUT"
  echo "AICORE_CLIENT_SECRET, AICORE_BASE_URL or do manual cockpit inventory (item d above)." >> "$OUT"
fi

# 8. Local Git status
section "Git status (sap-ai-journey)"
if [ -d "$HOME/repos/sap-ai-journey/.git" ]; then
  cd "$HOME/repos/sap-ai-journey"
  git status >> "$OUT" 2>&1
  echo "" >> "$OUT"
  echo "Unpushed commits:" >> "$OUT"
  git log origin/master..HEAD --oneline >> "$OUT" 2>&1 || echo "(branch may differ)" >> "$OUT"
  cd - > /dev/null
else
  echo "Repo not at ~/repos/sap-ai-journey — adjust path and re-run" >> "$OUT"
fi

# 9. Docker images
section "Docker images (srini117us namespace)"
docker images 2>/dev/null | grep -E "srini117us|REPOSITORY" >> "$OUT" || echo "Docker not available or no images" >> "$OUT"

echo "" >> "$OUT"
echo "=======================================" >> "$OUT"
echo "Inventory complete: $(date -Iseconds)" >> "$OUT"
echo ""
echo "Done. Review $OUT and the manual inventory files listed in section 6."
