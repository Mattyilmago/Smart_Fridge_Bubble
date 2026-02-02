#!/bin/bash
# Script per installare il servizio systemd Smart Fridge

echo "Installazione del servizio Smart Fridge..."

# Copia il file di servizio nella directory systemd
sudo cp /home/pub/Desktop/Smart_Fridge_Bubble/smart-fridge.service /etc/systemd/system/

# Ricarica i daemon di systemd
sudo systemctl daemon-reload

# Abilita il servizio per l'avvio automatico
sudo systemctl enable smart-fridge.service

# Avvia il servizio
sudo systemctl start smart-fridge.service

# Mostra lo stato del servizio
sudo systemctl status smart-fridge.service

echo ""
echo "Installazione completata!"
echo ""
echo "Comandi utili:"
echo "  - Vedere lo stato: sudo systemctl status smart-fridge"
echo "  - Fermare il servizio: sudo systemctl stop smart-fridge"
echo "  - Riavviare il servizio: sudo systemctl restart smart-fridge"
echo "  - Vedere i log: sudo journalctl -u smart-fridge -f"
echo "  - Disabilitare l'avvio automatico: sudo systemctl disable smart-fridge"
