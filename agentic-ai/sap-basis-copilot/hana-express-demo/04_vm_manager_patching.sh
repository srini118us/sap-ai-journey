#!/bin/bash
# Enable and run VM Manager OS patching on HANA Express VM
# Run from Cloud Shell

PROJECT="sap-basis-copilot"
ZONE="us-east4-b"
VM_NAME="hana-express-demo"

echo "=== Enabling VM Manager OS Config ==="
gcloud compute instances add-metadata $VM_NAME \
  --zone=$ZONE \
  --metadata=enable-osconfig=TRUE \
  --project=$PROJECT

echo "=== Installing OS Config agent on VM ==="
gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT -- \
  "sudo zypper install -y google-osconfig-agent && sudo systemctl enable google-osconfig-agent && sudo systemctl start google-osconfig-agent"

echo "=== Creating patch baseline ==="
gcloud compute os-config patch-deployments create hana-express-patches \
  --project=$PROJECT \
  --vm-name-prefixes=hana-express \
  --zypper-with-update \
  --one-time

echo "=== Running patch job ==="
gcloud compute os-config patch-jobs execute \
  --project=$PROJECT \
  --instance-filter-names="zones/$ZONE/instances/$VM_NAME" \
  --duration=2h \
  --reboot-config=DEFAULT \
  --description="HANA Express VM OS patching demo"

echo "=== Monitor patch job at: ==="
echo "https://console.cloud.google.com/compute/patch-jobs?project=$PROJECT"
