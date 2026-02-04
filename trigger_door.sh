#!/bin/bash
echo "🚪 Triggering door close with touch /tmp/fridge_door_trigger..."
touch /tmp/fridge_door_trigger
echo "✓ Done! Checking daemon log: tail -f ~/Desktop/Smart_Fridge_Bubble/logs/daemon.log"
tail -f ~/Desktop/Smart_Fridge_Bubble/logs/daemon.log