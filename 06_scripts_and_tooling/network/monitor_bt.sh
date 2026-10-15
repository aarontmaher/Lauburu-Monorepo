#!/bin/bash
for i in {1..300}; do
  if ifconfig | grep -q "bnep"; then
    echo "BLUETOOTH PAN DETECTED!"
    ifconfig | grep -A 3 "bnep"
    exit 0
  fi
  sleep 2
done
