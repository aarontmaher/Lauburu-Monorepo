#!/bin/bash
while true; do
  URL=$(osascript -e 'tell application "Google Chrome" to get URL of active tab of window 1' 2>/dev/null)
  echo "Current URL: $URL"
  if [[ "$URL" == *"sl/list"* ]]; then
    echo "✅ User logged in! Resuming."
    exit 0
  fi
  sleep 5
done
