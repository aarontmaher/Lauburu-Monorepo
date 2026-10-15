#!/bin/bash
echo "Monitoring router for Port 2 UP or IP 192.168.8.199..."
for i in {1..120}; do
  if ssh -o StrictHostKeyChecking=no root@192.168.8.1 "swconfig dev switch0 show | grep 'port:2 link:up'"; then
    echo "PORT 2 IS UP!"
    exit 0
  fi
  if ssh -o StrictHostKeyChecking=no root@192.168.8.1 "cat /proc/net/arp | grep '192.168.8.199'"; then
    echo "IP 199 IS ALIVE!"
    exit 0
  fi
  sleep 5
done
echo "Timeout reached."
exit 1
