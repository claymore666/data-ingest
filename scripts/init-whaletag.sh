#!/bin/bash
# Whale Tag Simulator initialization script
# SSH server and DHCP client are pre-installed in the Docker image

set -e

echo "Initializing whale tag simulator..."

# Run DHCP client to get IP from router (macvlan mode only)
# In bridge/host mode, skip DHCP and use Docker-assigned IP
if [ "$NETWORK_MODE" = "macvlan" ]; then
    # Macvlan mode - request DHCP lease from router
    echo "Macvlan mode - requesting DHCP lease..."
    if timeout 5 dhcpcd -1 eth0 2>&1 | grep -q "leased"; then
        echo "DHCP lease obtained: $(ip addr show eth0 | grep 'inet ' | awk '{print $2}' | head -1)"
    else
        echo "DHCP request failed (using Docker-assigned IP)"
    fi
else
    # Bridge or host mode - skip DHCP
    echo "Bridge mode - using Docker-assigned IP"
fi

# Create user pi with password ceticeti (if not exists)
if ! id pi > /dev/null 2>&1; then
    adduser -D -s /bin/bash pi
    echo "pi:${WHALETAG_PASSWORD:-ceticeti}" | chpasswd
fi

# Ensure /data directory ownership
chown pi:pi /data

# Create sample test files (as user pi)
su - pi <<'EOSU'
cd /data

# Create sample audio files (empty placeholders)
touch audio_2025-01-15_10-30-00.raw
touch audio_2025-01-15_11-00-00.raw
touch audio_2025-01-15_11-30-00.flac

# Create sample CSV sensor data
cat > sensors_2025-01-15.csv <<EOF
timestamp,temperature,pressure,depth
2025-01-15T10:30:00Z,18.5,101325,0
2025-01-15T11:00:00Z,17.2,110000,50
2025-01-15T11:30:00Z,16.8,120000,100
EOF

echo "Test data created in /data/"
EOSU

# Hostname is already set by Docker Compose
# No need to set it again (and would require privileged mode)

echo "Whale tag simulator initialized successfully!"
echo "Hostname: $(hostname)"
echo "SSH user: pi"
echo "SSH password: ${WHALETAG_PASSWORD:-ceticeti}"
echo "Data directory: /data"

# Start SSH server in foreground
echo "Starting SSH server..."
exec /usr/sbin/sshd -D
