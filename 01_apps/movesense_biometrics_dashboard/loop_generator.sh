#!/bin/bash
DESIGN_FILE="DESIGN.MD"
OUTPUT_FILE="scaffolded_app.py"
LAST_MTIME=0

echo "Starting UI Generation shell loop for $DESIGN_FILE..."

while true; do
    if [ -f "$DESIGN_FILE" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            CURRENT_MTIME=$(stat -f %m "$DESIGN_FILE")
        else
            CURRENT_MTIME=$(stat -c %Y "$DESIGN_FILE")
        fi
        
        if [ "$CURRENT_MTIME" -gt "$LAST_MTIME" ]; then
            echo "[$(date +%T)] Detected changes in $DESIGN_FILE, regenerating UI..."
            python3 ui_generator.py
            if [ $? -eq 0 ]; then
                if python3 -m py_compile "$OUTPUT_FILE" >/dev/null 2>&1; then
                    echo "[$(date +%T)] Scaffolded and syntax-checked $OUTPUT_FILE successfully."
                else
                    echo "[$(date +%T)] Generated $OUTPUT_FILE contains syntax errors."
                fi
            else
                echo "[$(date +%T)] ui_generator.py failed."
            fi
            LAST_MTIME=$CURRENT_MTIME
        fi
    fi
    sleep 5
done
