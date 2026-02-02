"""
Smart Fridge Monitor - Entry Point
Applicazione per monitoraggio temperatura e consumi frigorifero intelligente.

Componenti:
- Sensori temperatura e potenza (mock per sviluppo)
- Visualizzazione real-time con grafici
- Pubblicità da supermercati locali
- Sincronizzazione con server (opzionale)

Autore: Baricco
Progetto: IOT Smart Fridge
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui import MainWindow
from config import WINDOW_TITLE

# Force unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'


def main():
    """
    Funzione principale dell'applicazione.
    Inizializza QApplication e MainWindow.
    """
    print("=" * 60)
    print(f"{WINDOW_TITLE} - Starting...")
    print("=" * 60)
    
    # Crea QApplication
    app = QApplication(sys.argv)
    app.setApplicationName(WINDOW_TITLE)
    
    # Nascondi cursore in modalità kiosk (decommenta per produzione)
    # QApplication.setOverrideCursor(Qt.BlankCursor)
    
    # Crea e mostra finestra principale
    window = MainWindow()
    
    # Modalità fullscreen per Raspberry (decommenta per produzione)
    # window.showFullScreen()
    
    # Modalità normale per sviluppo (commenta in produzione)
    #window.resize(768, 1300)
    window.showFullScreen()
    
    print("[App] Application started successfully")
    print("[App] Press Ctrl+C in terminal or close window to exit")
    
    # Event loop
    exit_code = app.exec()
    
    print("\n" + "=" * 60)
    print(f"{WINDOW_TITLE} - Shutdown complete")
    print("=" * 60)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()