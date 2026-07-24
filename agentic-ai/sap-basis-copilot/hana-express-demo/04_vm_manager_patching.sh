#!/bin/bash
# Parameterized VM Manager OS Patching Script
# Usage: bash 04_vm_manager_patching.sh [SID] [ZONE] [PROJECT]
# Example: bash 04_vm_manager_patching.sh HXE us-east4-b sap-basis-copilot

SID=${1:-HXE}
ZONE=${2:-us-east4-b}
PROJECT=${3:-sap-basis-copilot}
SID_LOWER=$(echo $SID | tr '[:upper:]' '[:lower:]')
VM_NAME="${SID_LOWER}-hana-demo"

echo "=== Enabling VM Manager OS Patching ==="
echo "VM      : $VM_NAME"
echo "Zone    : $ZONE"
echo "Project : $PROJECT"
echo ""

# Enable OS Config
gcloud compute instances add-metadata $VM_NAME \
  --zone=$ZONE \
  --project=$PROJECT \
  --metadata=enable-osconfig=TRUE

# Install OS Config agent
gcloud compute ssh $VM_NAME \
  --zone=$ZONE \
  --project=$PROJECT \
  --command="sudo zypper install -y google-osconfig-agent 2>/dev/null || true && sudo systemctl enable google-osconfig-agent && sudo systemctl start google-osconfig-agent && echo 'OS Config agent running!'"

# Run patch job
echo "=== Running OS Patch Job ==="
gcloud compute os-config patch-jobs execute \
  --project=$PROJECT \
  --instance-filter-names="zones/$ZONE/instances/$VM_NAME" \
  --duration=2h \
  --reboot-config=DEFAULT \
  --description="$SID HANA Express VM OS patching"

echo ""
echo "=== Monitor at: ==="
echo "https://console.cloud.google.com/compute/patch-jobs?project=$PROJECT"
