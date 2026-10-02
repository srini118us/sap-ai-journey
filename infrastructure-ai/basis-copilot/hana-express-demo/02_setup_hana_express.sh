#!/bin/bash
# Parameterized HANA Express Setup Script
# Usage: bash 02_setup_hana_express.sh [SID] [HOSTNAME] [VM_IP] [PASSWORD]
# Example: bash 02_setup_hana_express.sh HXE hxehost YOUR_VM_IP CHANGE_ME

set -e

SID=${1:-HXE}
HOSTNAME=${2:-hxehost}
VM_IP=${3:-YOUR_VM_IP}
PASSWORD=${4:-CHANGE_ME}
PROJECT=${5:-sap-basis-copilot}
ZONE=${6:-us-east4-b}
SID_LOWER=$(echo $SID | tr '[:upper:]' '[:lower:]')
VM_NAME="${SID_LOWER}-hana-demo"
DATA_DIR="/data/${SID_LOWER}"

echo "=== HANA Express Setup ==="
echo "SID       : $SID"
echo "Hostname  : $HOSTNAME"
echo "VM IP     : $VM_IP"
echo "Data Dir  : $DATA_DIR"
echo ""

gcloud compute ssh $VM_NAME \
  --zone=$ZONE \
  --project=$PROJECT \
  --command="
set -e
echo '=== Installing Docker ==='
sudo zypper install -y docker 2>/dev/null || true
sudo systemctl enable docker
sudo systemctl start docker

echo '=== Setting Kernel Parameters ==='
sudo tee -a /etc/sysctl.conf << SYSCTL
fs.file-max=20000000
vm.max_map_count=135217728
kernel.shmmax=1073741824
kernel.shmall=8388608
SYSCTL
sudo sysctl -p 2>/dev/null || true

echo '=== Creating HANA Data Directory ==='
sudo mkdir -p $DATA_DIR
sudo chmod 777 $DATA_DIR

echo '=== Creating Password File ==='
sudo tee $DATA_DIR/${SID_LOWER}passwd.json << PASS
{"master_password": "$PASSWORD"}
PASS
sudo chmod 600 $DATA_DIR/${SID_LOWER}passwd.json
sudo chown 12000:79 $DATA_DIR/${SID_LOWER}passwd.json

echo '=== Setup Complete! ==='
echo 'Next: docker login, then bash 03_run_hana_express.sh'
"
