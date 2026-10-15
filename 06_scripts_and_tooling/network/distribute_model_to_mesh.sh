#!/bin/bash
MODEL_PATH="/Users/aaron/.local/share/models/gemma-4-31B-it-Q4_K_M.gguf"
echo "Distributing model to L5..."
rsync -avz --partial --append -e "ssh -F /dev/null -o StrictHostKeyChecking=no" --progress "$MODEL_PATH" aaronmaher@100.121.202.34:/tmp/
echo "Done."
