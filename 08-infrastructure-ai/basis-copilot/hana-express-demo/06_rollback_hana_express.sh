#!/bin/bash
# HANA Express Rollback Script
# Usage: bash 06_rollback_hana_express.sh [BACKUP_DIR] [FROM_TAG]
# Example: bash 06_rollback_hana_express.sh /data/hxe_backup_20260714_123456 2.00.076.00.20240701.1

BACKUP_DIR=${1:-}
FROM_TAG=${2:-2.00.076.00.20240701.1}
ZONE=${3:-us-east4-b}
PROJECT=${4:-sap-basis-copilot}
VM_NAME="hana-express-demo"
CONTAINER_NAME="hxe"
DATA_DIR="/data/hxe"

if [ -z "$BACKUP_DIR" ]; then
    echo "ERROR: Please provide backup directory path"
    echo "Usage: bash 06_rollback_hana_express.sh /data/hxe_backup_YYYYMMDD_HHMMSS"
    exit 1
fi

echo "=== HANA Express Rollback ==="
echo "Backup Dir : $BACKUP_DIR"
echo "From Tag   : $FROM_TAG"
echo ""

gcloud compute ssh $VM_NAME \
  --zone=$ZONE --project=$PROJECT \
  --command="
echo '=== ROLLBACK: Stopping current container ==='
sudo docker stop $CONTAINER_NAME 2>/dev/null || true
sudo docker rm $CONTAINER_NAME 2>/dev/null || true

echo '=== ROLLBACK: Restoring data from backup ==='
sudo rm -rf $DATA_DIR
sudo cp -rp $BACKUP_DIR $DATA_DIR
echo 'Data restored from backup'

echo '=== ROLLBACK: Starting previous HANA version ==='
sudo docker run \
  --stop-timeout 3600 \
  -d \
  --name $CONTAINER_NAME \
  -h hxehost \
  -p 39013:39013 -p 39017:39017 \
  -p 39041-39045:39041-39045 \
  -p 1128-1129:1128-1129 \
  -p 59013-59014:59013-59014 \
  -v $DATA_DIR:/hana/mounts \
  --ulimit nofile=1048576:1048576 \
  --sysctl kernel.shmmax=1073741824 \
  --sysctl 'net.ipv4.ip_local_port_range=40000 60999' \
  --sysctl kernel.shmall=8388608 \
  saplabs/hanaexpress:$FROM_TAG \
  --passwords-url file:///hana/mounts/hxepasswd.json \
  --agree-to-sap-license \
  --dont-check-system

echo 'Waiting 8 minutes for HANA to start...'
sleep 480
sudo docker ps --filter name=$CONTAINER_NAME
echo '=== ROLLBACK COMPLETE ==='
"
