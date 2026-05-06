#!/bin/bash
# ══════════════════════════════════════════════════════════════
# Spin up a test VM with Tomcat for agent testing
# Cost: $0 (e2-micro is free tier eligible)
# ══════════════════════════════════════════════════════════════

set -e

# ── CONFIGURATION ─────────────────────────────────────────────
PROJECT_ID="your-project-id"           # Your GCP project
ZONE="us-central1-a"                   # Free tier zone
VM_NAME="agent-test-vm"
MACHINE_TYPE="e2-micro"                # Free tier eligible

echo "Step 1: Creating VM..."
gcloud compute instances create ${VM_NAME} \
    --project=${PROJECT_ID} \
    --zone=${ZONE} \
    --machine-type=${MACHINE_TYPE} \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB \
    --metadata=enable-oslogin=TRUE \
    --tags=http-server \
    --quiet

echo "Step 2: Waiting for VM to be ready..."
sleep 30

echo "Step 3: Installing Tomcat..."
gcloud compute ssh ${VM_NAME} \
    --zone=${ZONE} \
    --project=${PROJECT_ID} \
    --command="
        sudo apt-get update -y && \
        sudo apt-get install -y default-jdk tomcat9 tomcat9-admin curl && \
        sudo systemctl enable tomcat9 && \
        sudo systemctl start tomcat9 && \
        echo 'Tomcat installed and running' && \
        curl -s -o /dev/null -w '%{http_code}' http://localhost:8080
    "

echo "Step 4: Opening firewall for HTTP (optional, for browser testing)..."
gcloud compute firewall-rules create allow-tomcat \
    --project=${PROJECT_ID} \
    --allow=tcp:8080 \
    --target-tags=http-server \
    --description="Allow Tomcat access for testing" \
    --quiet 2>/dev/null || echo "Firewall rule already exists"

# Get VM internal IP
INTERNAL_IP=$(gcloud compute instances describe ${VM_NAME} \
    --zone=${ZONE} \
    --project=${PROJECT_ID} \
    --format="get(networkInterfaces[0].networkIP)")

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  VM Ready!"
echo "══════════════════════════════════════════════════════════"
echo "  VM Name:     ${VM_NAME}"
echo "  Zone:        ${ZONE}"
echo "  Internal IP: ${INTERNAL_IP}"
echo "  Tomcat:      http://${INTERNAL_IP}:8080"
echo ""
echo "  Test SSH:    gcloud compute ssh ${VM_NAME} --zone=${ZONE}"
echo "  Test Tomcat: gcloud compute ssh ${VM_NAME} --zone=${ZONE} --command='curl -s -o /dev/null -w \"%{http_code}\" http://localhost:8080'"
echo "══════════════════════════════════════════════════════════"
echo ""
echo "  Update your agent's .env file with:"
echo "  VM_NAME=${VM_NAME}"
echo "  VM_ZONE=${ZONE}"
echo "  VM_PROJECT=${PROJECT_ID}"
echo "══════════════════════════════════════════════════════════"
