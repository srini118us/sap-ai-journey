#!/bin/bash
# Run this script ON the HANA Express VM after it is created
# Usage: bash setup_hana_express.sh

set -e
echo "=== Setting up HANA Express on GCP VM ==="

# 1. Install Docker
echo "Installing Docker..."
zypper install -y docker
systemctl enable docker
systemctl start docker

# 2. Set kernel parameters required for HANA
echo "Setting kernel parameters..."
cat >> /etc/sysctl.conf << SYSCTL
fs.file-max=20000000
vm.max_map_count=135217728
kernel.shmmax=1073741824
kernel.shmmni=524288
kernel.shmall=8388608
SYSCTL
sysctl -p

# 3. Create data directory for HANA mounts
echo "Creating HANA data directory..."
mkdir -p /data/hxe
chmod 777 /data/hxe

# 4. Create password file
echo "Creating HANA password file..."
cat > /data/hxe/hxepasswd.json << PASS
{"master_password": "HanaExpr2026#"}
PASS
chmod 600 /data/hxe/hxepasswd.json
chown 12000:79 /data/hxe/hxepasswd.json

echo "=== Setup complete! Now run: ==="
echo "1. docker login   (use your Docker Hub credentials)"
echo "2. docker pull saplabs/hanaexpress:2.00.061.00.20220519.1"
echo "3. bash run_hana_express.sh"
