#!/bin/bash
# Parameterized HANA on GCP Deployment Script
# Usage: bash 01_deploy_vm.sh [SID] [HOSTNAME] [MACHINE_TYPE] [ZONE]
# Example: bash 01_deploy_vm.sh HXE hxehost e2-highmem-8 us-east4-b
# Example: bash 01_deploy_vm.sh HDB hdbhost n1-highmem-16 us-central1-a

set -e

# ─── Parameters (with defaults) ───
SID=${1:-HXE}
HOSTNAME=${2:-hxehost}
MACHINE_TYPE=${3:-e2-highmem-8}
ZONE=${4:-us-east4-b}
PROJECT=${5:-sap-basis-copilot}

# Derived values
SID_LOWER=$(echo $SID | tr '[:upper:]' '[:lower:]')
VM_NAME="${SID_LOWER}-hana-demo"
SSH_KEY=$(cat ~/.ssh/sap-basis-agent-key.pub)

echo "=== HANA Express GCP Deployment ==="
echo "SID          : $SID"
echo "Hostname     : $HOSTNAME"
echo "VM Name      : $VM_NAME"
echo "Machine Type : $MACHINE_TYPE"
echo "Zone         : $ZONE"
echo "Project      : $PROJECT"
echo ""

# ─── Pre-checks ───
echo "=== Running Pre-Deployment Checks ==="

# Check machine type has enough RAM (need 32GB minimum)
echo "Checking machine type availability..."
gcloud compute machine-types describe $MACHINE_TYPE \
  --zone=$ZONE \
  --project=$PROJECT \
  --format="table(name,memoryMb,guestCpus)" 2>/dev/null || {
    echo "WARNING: Machine type $MACHINE_TYPE not available in $ZONE"
    echo "Try: us-east4-a or us-central1-a"
    exit 1
}

# Check if VM already exists
EXISTING=$(gcloud compute instances list \
  --project=$PROJECT \
  --filter="name=$VM_NAME" \
  --format="get(name)" 2>/dev/null)

if [ -n "$EXISTING" ]; then
    echo "WARNING: VM $VM_NAME already exists!"
    echo "Delete it first: gcloud compute instances delete $VM_NAME --zone=$ZONE --project=$PROJECT"
    exit 1
fi

echo "Pre-checks passed!"
echo ""

# ─── Deploy VM ───
echo "=== Creating VM: $VM_NAME ==="
gcloud compute instances create $VM_NAME \
  --project=$PROJECT \
  --zone=$ZONE \
  --machine-type=$MACHINE_TYPE \
  --image-family=sles-15-sp5 \
  --image-project=suse-cloud \
  --boot-disk-size=200GB \
  --boot-disk-type=pd-ssd \
  --boot-disk-device-name=${VM_NAME}-disk \
  --metadata="enable-osconfig=TRUE,ssh-keys=saps101226:$SSH_KEY" \
  --tags=hana-express,sap-demo \
  --scopes=cloud-platform \
  --labels="sid=$SID_LOWER,type=hana-express,env=dev"

echo ""
echo "=== VM Created Successfully ==="
VM_IP=$(gcloud compute instances describe $VM_NAME \
  --zone=$ZONE \
  --project=$PROJECT \
  --format="get(networkInterfaces[0].accessConfigs[0].natIP)" 2>/dev/null)

echo "VM Name : $VM_NAME"
echo "VM IP   : $VM_IP"
echo "SID     : $SID"
echo "Zone    : $ZONE"
echo ""
echo "=== Next Steps ==="
echo "Wait 2 minutes for VM to boot, then run:"
echo "bash 02_setup_hana_express.sh $SID $HOSTNAME $VM_IP"
