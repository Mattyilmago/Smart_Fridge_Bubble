#!/bin/bash
# Ottieni la directory dello script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🚪 Triggering door close with touch /tmp/fridge_door_trigger..."
touch /tmp/fridge_door_trigger
echo "✓ Done! Checking daemon log: tail -f $SCRIPT_DIR/logs/daemon.log"
tail -f "$SCRIPT_DIR/logs/daemon.log"