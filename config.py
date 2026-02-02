# === CONFIGURAZIONI SENSORI ===
POLLING_INTERVAL_MS = 1000  # Intervallo polling sensori in millisecondi

# Range simulazione sensori mock
TEMPERATURE_RANGE = (0.0, 10.0)  # °C (temperatura tipica frigo)
POWER_RANGE = (50.0, 150.0)      # Watt (consumo tipico frigo)

# === CONFIGURAZIONI STORICO DATI ===
HISTORY_HOURS = 48  # Ore di storico da mantenere e visualizzare
# Calcola MAX_DATA_POINTS in base al polling interval
# Formula: ore * secondi_per_ora * millisecondi_per_secondo / intervallo_polling_ms
MAX_DATA_POINTS = int(HISTORY_HOURS * 3600 * 1000 / POLLING_INTERVAL_MS)

# === CONFIGURAZIONI API SERVER ===
API_BASE_URL = "http://localhost:5000"  # Da modificare con URL server reale (PLACEHOLDER)

# Token frigo salvato localmente
FRIDGE_TOKEN_FILE = "fridge_token.json"

# Validazione token ogni 24h
TOKEN_VALIDATION_INTERVAL_HOURS = 24

# Retry e timeout per richieste HTTP
API_MAX_RETRIES = 3
API_RETRY_DELAY_SECONDS = 5
API_REQUEST_TIMEOUT_SECONDS = 10

# Intervallo invio dati sensori al server (in secondi)
SENSOR_DATA_SEND_INTERVAL_SECONDS = 60  # Ogni minuto

# Endpoint API (legacy - mantenuto per compatibilità con UI esistente)
API_ENDPOINTS = {
    'temperature_history': '/temperature/history',
    'power_history': '/power/history',
    'temperature_post': '/temperature',
    'power_post': '/power'
}

# === CONFIGURAZIONI CAMERA (GoPro USB) ===
CAMERA_IMAGE_DIR = "captured_images"  # Directory per salvare immagini catturate
CAMERA_RESOLUTION = (1280, 720)       # Risoluzione immagini (width, height)
CAMERA_WARMUP_FRAMES = 5              # Frame da scartare prima di catturare (stabilizzazione)
CAMERA_MAX_RETRIES = 3                # Retry su errore cattura

# === CONFIGURAZIONI DOOR SENSOR (Reed Switch) ===
DOOR_GPIO_PIN = 17                    # Pin GPIO per reed switch (BCM numbering)
DOOR_DEBOUNCE_TIME_SECONDS = 0.1      # Tempo debouncing (100ms)
DOOR_USE_PULLUP = True                # True = pull-up, False = pull-down
DOOR_CLOSE_DELAY_SECONDS = 2.0        # Attesa dopo chiusura porta prima di scattare foto

# === CONFIGURAZIONI YOLO ===
YOLO_MODEL_PATH = "yolov8n.pt"        # Path modello YOLO (o "models/custom_food_model.pt")
YOLO_CONFIDENCE_THRESHOLD = 0.5       # Soglia minima confidence (0-1)
YOLO_MAX_RETRIES = 2                  # Retry su errore detection

# === CONFIGURAZIONI LOGGING ===
LOG_DIR = "logs"                      # Directory per file di log
LOG_MAX_FILE_SIZE_MB = 10             # Dimensione massima singolo file log (rotazione)
LOG_BACKUP_COUNT = 5                  # Numero file di backup da mantenere

# === CONFIGURAZIONI UI ===
WINDOW_TITLE = "Smart Fridge Monitor"
CHART_THEME = "dark"  # "light" o "dark"

# Proporzioni layout (percentuali)
ADS_HEIGHT_PERCENT = 50  # Pubblicità occupa 50% altezza
CHARTS_HEIGHT_PERCENT = 50  # Grafici occupano 50% altezza

# URL pubblicità di default (per testing)
DEFAULT_ADS_URL = "https://www.example.com"

# === CONFIGURAZIONI GRAFICI ===
CHART_X_AXIS_LABEL_INTERVAL = 1  # Etichetta ogni 1 ora
CHART_ANIMATION_DURATION = 200  # Durata animazione aggiornamento (ms)

# Soglie temperatura (°C) per zone colorate
TEMPERATURE_THRESHOLDS = {
    'safe_max': 20.0,      # Temperatura sicura massima (zona verde: <= 6°C)
    'warning_max': 24.0,   # Temperatura warning massima (zona gialla: 6-8°C)
    # Oltre 8°C = zona rossa (pericolo)
}

# Colori zone temperatura
TEMPERATURE_ZONE_COLORS = {
    'safe': '#2ECC71',      # Verde: temperatura ottimale (0-6°C)
    'warning': '#F39C12',   # Giallo/Arancione: attenzione (6-8°C)
    'danger': '#E74C3C',    # Rosso: pericolo (>8°C)
    'zone_opacity': 30      # Opacità zone (0-255)
}

# Colori grafici (tema scuro)
CHART_COLORS = {
    'temperature_line': '#4ECDC4',  # Azzurro per temperatura
    'power_line': '#FF6B6B',        # Rosso per potenza
    'average_line_temperature': '#1f524e',      # Azzurro scuro per media temperatura
    'average_line_power': '#662a2a',            # Rosso scuro per media potenza
    'background': '#111111',
    'grid': '#4F5D75',
    'text': '#FFFFFF'
}