#!/bin/bash
# Deploy HANA Express VM using gcloud (without Terraform)
# Run from Cloud Shell

PROJECT="sap-basis-copilot"
ZONE="us-east4-b"
VM_NAME="hana-express-demo"
SSH_KEY=$(cat ~/.ssh/sap-basis-agent-key.pub)

echo "=== Creating HANA Express VM ==="
gcloud compute instances create $VM_NAME \
  --project=$PROJECT \
  --zone=$ZONE \
  --machine-type=e2-highmem-8 \
  --image-family=sles-15-sp4-sap \
  --image-project=suse-sap-cloud \
  --boot-disk-size=200GB \
  --boot-disk-type=pd-ssd \
  --metadata="enable-osconfig=TRUE,ssh-keys=root:$SSH_KEY" \
  --tags=hana-express,sap-demo \
  --scopes=cloud-platform

echo "=== VM created! Getting IP... ==="
gcloud compute instances describe $VM_NAME \
  --zone=$ZONE \
  --project=$PROJECT \
  --format="get(networkInterfaces[0].accessConfigs[0].natIP)"

echo "=== Wait 2 minutes for VM to boot, then run: ==="
echo "ssh -i ~/.ssh/sap-basis-agent-key root@<VM_IP>"
echo "bash setup_hana_express.sh"
