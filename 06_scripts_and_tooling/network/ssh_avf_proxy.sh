#!/bin/bash
TARGET_IP=$1
TARGET_PORT=$2
ssh -F /dev/null -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no u0_a363@100.114.215.68 -p 8022 "~/bin/rish -c 'nc $TARGET_IP $TARGET_PORT' 2>&1"
