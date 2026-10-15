#!/bin/bash
for i in {1..300}; do
  if ssh -o StrictHostKeyChecking=no root@192.168.8.1 "swconfig dev switch0 show | grep 'port:2 link:up'"; then
    echo "PORT 2 IS UP!"
    exit 0
  fi
  sleep 5
done
