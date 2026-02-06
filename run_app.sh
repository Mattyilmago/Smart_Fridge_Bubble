#!/bin/bash
# Smart Fridge - Integrated Startup
# Avvia daemon in background, poi UI in foreground

# Ottieni la directory dello script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

source venv/bin/activate
export DISPLAY=:0
export PYTHONUNBUFFERED=1

# Crea directory logs se non esiste
mkdir -p logs

# Pulisci vecchio file sensori
rm -f /tmp/fridge_sensors.json

echo "=========================================="
echo "Smart Fridge - Starting..."
echo "=========================================="

# Avvia daemon in background
echo "[1/2] Starting daemon (background)..."
python fridge_daemon.py > logs/daemon.log 2>&1 &
DAEMON_PID=$!
echo "  ✓ Daemon started (PID: $DAEMON_PID)"

# Aspetta che daemon inizializzi i sensori (max 10s)
echo "[2/2] Waiting for daemon initialization..."
for i in {1..10}; do
    if [ -f "/tmp/fridge_sensors.json" ]; then
        echo "  ✓ Daemon ready!"
        break
    fi
    sleep 1
done

# Avvia UI in foreground
echo ""
echo "Starting UI (fullscreen)..."
python app.py

# Quando UI si chiude, termina anche il daemon
echo ""
echo "Shutting down daemon..."
kill $DAEMON_PID 2>/dev/null
wait $DAEMON_PID 2>/dev/null

echo "Smart Fridge stopped."