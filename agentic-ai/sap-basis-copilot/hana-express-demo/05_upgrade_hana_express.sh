#!/bin/bash
# HANA Express Upgrade Script
# Usage: bash 05_upgrade_hana_express.sh [FROM_VERSION] [TO_TAG] [ZONE] [PROJECT]
# Example: bash 05_upgrade_hana_express.sh 2.00.076 latest us-east4-b sap-basis-copilot

set -e

FROM_VERSION=${1:-2.00.076}
TO_TAG=${2:-latest}
ZONE=${3:-us-east4-b}
PROJECT=${4:-sap-basis-copilot}
VM_NAME="hana-express-demo"
CONTAINER_NAME="hxe"
DATA_DIR="/data/hxe"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/data/hxe_backup_${TIMESTAMP}"

echo "=== HANA Express Upgrade ==="
echo "From Version : $FROM_VERSION"
echo "To Tag       : $TO_TAG"
echo "VM           : $VM_NAME"
echo "Zone         : $ZONE"
echo ""

gcloud compute ssh $VM_NAME \
  --zone=$ZONE --project=$PROJECT \
  --command="
echo '=== STEP 1: PRE-CHECKS ==='
echo 'Current container status:'
sudo docker ps --filter name=$CONTAINER_NAME --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'

echo ''
echo 'Current HANA version:'
HDBSQL=\$(sudo docker exec $CONTAINER_NAME find /hana/shared -name hdbsql 2>/dev/null | head -1)
sudo docker exec $CONTAINER_NAME \$HDBSQL -i 90 -d HXE -u SYSTEM -p HanaExpr2026# 'SELECT VERSION FROM SYS.M_DATABASE' 2>/dev/null || echo 'HANA not responding yet'

echo ''
echo 'Disk space check:'
df -h $DATA_DIR | tail -1

echo ''
echo '=== STEP 2: BACKUP ==='
echo 'Creating backup of HANA data directory...'
sudo cp -rp $DATA_DIR $BACKUP_DIR
echo "Backup created: \$BACKUP_DIR"
echo "Backup size: \$(du -sh $BACKUP_DIR | cut -f1)"
echo 'BACKUP COMPLETE - safe to proceed with upgrade'

echo ''
echo '=== STEP 3: STOP HANA ==='
echo 'Stopping HANA container gracefully...'
sudo docker stop $CONTAINER_NAME
echo 'Waiting for clean shutdown...'
sleep 10
sudo docker rm $CONTAINER_NAME
echo 'Container stopped and removed'

echo ''
echo '=== STEP 4: PULL NEW IMAGE ==='
echo 'Pulling HANA Express $TO_TAG...'
sudo docker pull saplabs/hanaexpress:$TO_TAG
echo 'New image pulled successfully'

echo ''
echo '=== STEP 5: START UPGRADED HANA ==='
echo 'Starting HANA with new image (data preserved)...'
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
  saplabs/hanaexpress:$TO_TAG \
  --passwords-url file:///hana/mounts/hxepasswd.json \
  --agree-to-sap-license \
  --dont-check-system
echo 'New container started - waiting 8 minutes for HANA to initialize...'
sleep 480

echo ''
echo '=== STEP 6: POST-CHECKS ==='
echo 'New container status:'
sudo docker ps --filter name=$CONTAINER_NAME --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'

echo ''
echo 'New HANA version:'
HDBSQL=\$(sudo docker exec $CONTAINER_NAME find /hana/shared -name hdbsql 2>/dev/null | head -1)
NEW_VER=\$(sudo docker exec $CONTAINER_NAME \$HDBSQL -i 90 -d HXE -u SYSTEM -p HanaExpr2026# 'SELECT VERSION FROM SYS.M_DATABASE' 2>/dev/null)
echo "\$NEW_VER"

echo ''
echo 'SQL connectivity test:'
sudo docker exec $CONTAINER_NAME \$HDBSQL -i 90 -d HXE -u SYSTEM -p HanaExpr2026# 'SELECT * FROM DUMMY'

echo ''
echo 'All HANA services status:'
sudo docker exec $CONTAINER_NAME \$HDBSQL -i 90 -d HXE -u SYSTEM -p HanaExpr2026# 'SELECT SERVICE_NAME, PORT, ACTIVE_STATUS FROM SYS.M_SERVICES ORDER BY SERVICE_NAME'

echo ''
echo 'Database active status:'
sudo docker exec $CONTAINER_NAME \$HDBSQL -i 90 -d HXE -u SYSTEM -p HanaExpr2026# 'SELECT DATABASE_NAME, ACTIVE_STATUS, VERSION FROM SYS.M_DATABASE'

echo ''
echo 'Memory utilization:'
sudo docker exec $CONTAINER_NAME \$HDBSQL -i 90 -d HXE -u SYSTEM -p HanaExpr2026# 'SELECT HOST, ROUND(USED_PHYSICAL_MEMORY/1024/1024/1024,2) AS USED_GB, ROUND(TOTAL_MEMORY_SIZE/1024/1024/1024,2) AS TOTAL_GB FROM SYS.M_HOST_RESOURCE_UTILIZATION'

echo ''
echo '=== UPGRADE COMPLETE ==='
echo "HANA upgraded from $FROM_VERSION to: \$NEW_VER"
echo "Backup available at: $BACKUP_DIR"
echo 'If issues found - run rollback script: bash 06_rollback_hana_express.sh'
"
