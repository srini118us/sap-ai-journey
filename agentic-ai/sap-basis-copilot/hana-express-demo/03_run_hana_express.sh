#!/bin/bash
# Run HANA Express container
# Usage: bash run_hana_express.sh

echo "=== Starting HANA Express container ==="

docker run \
  --stop-timeout 3600 \
  -i \
  --name hxe \
  -h hxehost \
  -p 39013:39013 \
  -p 39017:39017 \
  -p 39041-39045:39041-39045 \
  -p 1128-1129:1128-1129 \
  -p 59013-59014:59013-59014 \
  -v /data/hxe:/hana/mounts \
  --ulimit nofile=1048576:1048576 \
  --sysctl kernel.shmmax=1073741824 \
  --sysctl "net.ipv4.ip_local_port_range=40000 60999" \
  --sysctl kernel.shmmni=524288 \
  --sysctl kernel.shmall=8388608 \
  saplabs/hanaexpress:2.00.061.00.20220519.1 \
  --passwords-url file:///hana/mounts/hxepasswd.json \
  --agree-to-sap-license

echo "=== HANA Express started! ==="
echo "Connect: hdbsql -i 90 -d HXE -u SYSTEM -p HanaExpr2026#"
