#!/bin/bash
# Parameterized HANA Express Docker Run Script
# Usage: bash 03_run_hana_express.sh [SID] [HOSTNAME] [VM_IP] [PASSWORD]
# Example: bash 03_run_hana_express.sh HXE hxehost 34.48.207.206 HanaExpr2026#

SID=${1:-HXE}
HOSTNAME=${2:-hxehost}
VM_IP=${3:-34.48.207.206}
PASSWORD=${4:-HanaExpr2026#}
PROJECT=${5:-sap-basis-copilot}
ZONE=${6:-us-east4-b}
SID_LOWER=$(echo $SID | tr '[:upper:]' '[:lower:]')
VM_NAME="${SID_LOWER}-hana-demo"
DATA_DIR="/data/${SID_LOWER}"
CONTAINER_NAME="${SID_LOWER}"

echo "=== Starting HANA Express Container ==="
echo "SID        : $SID"
echo "Hostname   : $HOSTNAME"
echo "Container  : $CONTAINER_NAME"
echo "Data Dir   : $DATA_DIR"
echo ""

gcloud compute ssh $VM_NAME \
  --zone=$ZONE \
  --project=$PROJECT \
  --command="
# Remove existing container if any
sudo docker rm $CONTAINER_NAME 2>/dev/null || true

echo 'Pulling HANA Express image...'
sudo docker pull saplabs/hanaexpress:latest

echo 'Starting HANA Express container...'
sudo docker run \
  --stop-timeout 3600 \
  -d \
  --name $CONTAINER_NAME \
  -h $HOSTNAME \
  -p 39013:39013 \
  -p 39017:39017 \
  -p 39041-39045:39041-39045 \
  -p 1128-1129:1128-1129 \
  -p 59013-59014:59013-59014 \
  -v $DATA_DIR:/hana/mounts \
  --ulimit nofile=1048576:1048576 \
  --sysctl kernel.shmmax=1073741824 \
  --sysctl 'net.ipv4.ip_local_port_range=40000 60999' \
  --sysctl kernel.shmall=8388608 \
  saplabs/hanaexpress:latest \
  --passwords-url file:///hana/mounts/${SID_LOWER}passwd.json \
  --agree-to-sap-license \
  --dont-check-system

echo 'Container started! Waiting 5 minutes for HANA to initialize...'
sleep 300

echo 'Verifying HANA is running...'
HDBSQL=\$(sudo docker exec $CONTAINER_NAME find /hana/shared -name hdbsql 2>/dev/null | head -1)
sudo docker exec $CONTAINER_NAME \$HDBSQL -i 90 -d $SID -u SYSTEM -p $PASSWORD 'SELECT * FROM DUMMY'
echo 'HANA $SID is ready!'
"
