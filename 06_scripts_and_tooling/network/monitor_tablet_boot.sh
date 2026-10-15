#!/bin/bash
echo "Monitoring router for tablet booting up..."
for i in {1..60}; do
  if ssh -o StrictHostKeyChecking=no root@192.168.8.1 "swconfig dev switch0 show | grep 'port:2 link:up'"; then
    echo "TABLET ETHERNET PORT 2 IS UP!"
    exit 0
  fi
  
  if ssh -o StrictHostKeyChecking=no root@192.168.8.1 "cat /proc/net/arp | grep -v '00:00:00:00:00:00' | wc -l" > /tmp/arp_count; then
    # Just keeping it polling silently
    :
  fi
  sleep 2
done
echo "Timeout."
exit 1
