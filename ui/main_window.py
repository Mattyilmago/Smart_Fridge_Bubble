"""
MainWindow: finestra principale dell'applicazione.
Layout verticale:
- Metà superiore: pubblicità (AdsWidget)
- Metà inferiore: 2 grafici stacked (temperatura e potenza)
"""

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSplitter
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPalette
from .ads_widget import AdsWidget
from .chart_widget import ChartWidget
from sensors.shared_sensors import SharedTemperatureSensor as TemperatureSensor, SharedPowerSensor as PowerSensor
from data import DataManager
from config import (WINDOW_TITLE, ADS_HEIGHT_PERCENT, CHARTS_HEIGHT_PERCENT,
                   POLLING_INTERVAL_MS, CHART_COLORS, HISTORY_HOURS)


class MainWindow(QMainWindow):
    """
    Finestra principale dell'applicazione Smart Fridge.
    Gestisce layout, timer polling sensori, e aggiornamento UI.
    """
    
    def __init__(self):
        super().__init__()
        
        # Inizializza sensori
        self.temp_sensor = TemperatureSensor()
        self.power_sensor = PowerSensor()
        
        # Inizializza data managers (API disabilitata per ora)
        self.temp_data_manager = DataManager('temperature', api_enabled=False)
        self.power_data_manager = DataManager('power', api_enabled=False)
        
        # Setup UI
        self._setup_ui()
        
        # Inizializza sensori
        self._initialize_sensors()
        
        # Carica storico da server (se API abilitata)
        self._load_history()
        
        # Setup timer polling
        self._setup_polling_timer()
        
        print("[MainWindow] Initialization complete")
    
    def _setup_ui(self):
        """Configura layout e widget della finestra."""
        self.setWindowTitle(WINDOW_TITLE)
        
        # Imposta tema scuro globale
        self._set_dark_theme()
        
        # Widget centrale
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principale verticale
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # === SEZIONE SUPERIORE: Pubblicità ===
        self.ads_widget = AdsWidget()
        
        # === SEZIONE INFERIORE: Grafici ===
        # Container per grafici
        charts_widget = QWidget()
        charts_layout = QVBoxLayout(charts_widget)
        charts_layout.setContentsMargins(5, 5, 5, 5)
        charts_layout.setSpacing(10)
        
        # Grafico temperatura
        self.temp_chart = ChartWidget(
            title="Temperature",
            unit="°C",
            line_color=CHART_COLORS['temperature_line'],
            average_line_color=CHART_COLORS['average_line_temperature'],
            enable_temp_zones=True  # Abilita zone colorate per temperatura
        )
        
        # Grafico potenza
        self.power_chart = ChartWidget(
            title="Power Consumption",
            unit="W",
            line_color=CHART_COLORS['power_line'],
            average_line_color=CHART_COLORS['average_line_power']
        )
        
        charts_layout.addWidget(self.temp_chart)
        charts_layout.addWidget(self.power_chart)
        
        # === SPLITTER per dividere ads e grafici ===
        # Usa QSplitter per rispettare proporzioni 50/50
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.ads_widget)
        splitter.addWidget(charts_widget)
        
        # Imposta proporzioni iniziali (50% ciascuno)
        # Calcola altezza stimata (800px di default)
        total_height = 800
        ads_height = int(total_height * ADS_HEIGHT_PERCENT / 100)
        charts_height = int(total_height * CHARTS_HEIGHT_PERCENT / 100)
        splitter.setSizes([ads_height, charts_height])
        
        # Disabilita resize manuale (opzionale)
        splitter.setChildrenCollapsible(False)
        
        main_layout.addWidget(splitter)
    
    def _set_dark_theme(self):
        """Applica tema scuro all'applicazione."""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(CHART_COLORS['background']))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(CHART_COLORS['text']))
        palette.setColor(QPalette.ColorRole.Base, QColor(CHART_COLORS['background']))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(CHART_COLORS['grid']))
        palette.setColor(QPalette.ColorRole.Text, QColor(CHART_COLORS['text']))
        palette.setColor(QPalette.ColorRole.Button, QColor(CHART_COLORS['grid']))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(CHART_COLORS['text']))
        
        self.setPalette(palette)
    
    def _initialize_sensors(self):
        """Inizializza i sensori hardware."""
        print("[MainWindow] Initializing sensors...")
        
        success = True
        success &= self.temp_sensor.initialize()
        success &= self.power_sensor.initialize()
        
        if success:
            print("[MainWindow] All sensors initialized successfully")
        else:
            print("[MainWindow] Warning: Some sensors failed to initialize")
    
    def _load_history(self):
        """Carica lo storico dati dal server (se API abilitata)."""
        print("[MainWindow] Loading historical data...")
        
        self.temp_data_manager.load_history_from_server()
        self.power_data_manager.load_history_from_server()
        
        # Aggiorna grafici con dati storici (se disponibili)
        self._update_charts()
    
    def _setup_polling_timer(self):
        """Configura timer per polling periodico dei sensori."""
        self.polling_timer = QTimer()
        self.polling_timer.timeout.connect(self._poll_sensors)
        self.polling_timer.start(POLLING_INTERVAL_MS)
        
        print(f"[MainWindow] Polling timer started (interval: {POLLING_INTERVAL_MS}ms)")
    
    def _poll_sensors(self):
        """
        Callback timer: legge sensori e aggiorna dati.
        Chiamato ogni POLLING_INTERVAL_MS millisecondi.
        """
        # Leggi temperatura
        try:
            temp_value = self.temp_sensor.read()
            self.temp_data_manager.add_data_point(temp_value)
        except Exception as e:
            print(f"[MainWindow] Error reading temperature: {e}")
        
        # Leggi potenza
        try:
            power_value = self.power_sensor.read()
            self.power_data_manager.add_data_point(power_value)
        except Exception as e:
            print(f"[MainWindow] Error reading power: {e}")
        
        # Aggiorna grafici
        self._update_charts()
    
    def _update_charts(self):
        """Aggiorna i grafici con i dati più recenti."""
        # Ottieni dati ultime 48h
        temp_points = self.temp_data_manager.get_data_points(hours=HISTORY_HOURS)
        power_points = self.power_data_manager.get_data_points(hours=HISTORY_HOURS)
        
        # Calcola medie
        temp_avg = self.temp_data_manager.get_average(hours=HISTORY_HOURS)
        power_avg = self.power_data_manager.get_average(hours=HISTORY_HOURS)
        
        # Aggiorna widget grafici
        if temp_points:
            self.temp_chart.update_chart(temp_points, temp_avg)
        
        if power_points:
            self.power_chart.update_chart(power_points, power_avg)
    
    def showFullScreen(self):
        """Override per modalità fullscreen con messaggio."""
        super().showFullScreen()
        print("[MainWindow] Entered fullscreen mode")
    
    def closeEvent(self, event):
        """
        Override closeEvent per cleanup risorse.
        Chiamato quando la finestra viene chiusa.
        """
        print("[MainWindow] Shutting down...")
        
        # Stop timer
        if hasattr(self, 'polling_timer'):
            self.polling_timer.stop()
        
        # Cleanup sensori
        self.temp_sensor.cleanup()
        self.power_sensor.cleanup()
        
        print("[MainWindow] Cleanup complete")
        event.accept()