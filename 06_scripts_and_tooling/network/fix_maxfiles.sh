#!/bin/bash
echo "Increasing maxfiles limit..."
sudo sysctl -w kern.maxfiles=1048576
sudo sysctl -w kern.maxfilesperproc=1048576
ulimit -n 65536
echo "Restarting SeaweedFS volume and filer services..."
launchctl stop ai.lauburu.seaweedfs-vol1
launchctl stop ai.lauburu.seaweedfs-filer
sleep 2
launchctl start ai.lauburu.seaweedfs-filer
launchctl start ai.lauburu.seaweedfs-vol1
echo "Done."
