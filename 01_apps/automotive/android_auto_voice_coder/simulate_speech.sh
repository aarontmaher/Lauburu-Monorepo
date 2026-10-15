#!/bin/bash
TRANSCRIPT="$1"
DEVICE_TARGET=""
if [ ! -z "$2" ]; then DEVICE_TARGET="-s $2"; fi
echo "Simulating Speech: \"$TRANSCRIPT\""
# Use single quotes inside double quotes to protect spaces from the Android shell
adb $DEVICE_TARGET shell am broadcast -a com.lauburu.intent.action.SIMULATE_SPEECH --es "transcript" "'$TRANSCRIPT'"
echo "Command Dispatched."
