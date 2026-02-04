"""
Fridge Daemon: orchestratore principale dello smart fridge.

ResponsabilitÃ :
- Monitora apertura/chiusura porta frigo
- Cattura foto quando porta si chiude
- Esegue detection prodotti con YOLO
- Invia prodotti riconosciuti al server
- Invia dati temp/consumi aggregati ogni minuto
- Gestisce retry ed errori
"""

import time
import threading
import json
from datetime import datetime, timedelta
from typing import List, Tuple
from collections import deque
from pathlib import Path

# Import con path corretti per la tua struttura
from image_recognition.camera_manager import CameraManager
from sensors.door_sensor import DoorSensor
from image_recognition.yolo_detector import YOLODetector
from data.server_api import ServerAPI
from sensors import TemperatureSensor, PowerSensor
from data import DataManager
from logger.logger import get_logger, log_error_for_server

from config import (
    API_BASE_URL, FRIDGE_TOKEN_FILE, API_MAX_RETRIES, API_RETRY_DELAY_SECONDS,
    CAMERA_IMAGE_DIR, CAMERA_RESOLUTION, CAMERA_WARMUP_FRAMES, CAMERA_MAX_RETRIES,
    DOOR_GPIO_PIN, DOOR_DEBOUNCE_TIME_SECONDS, DOOR_USE_PULLUP, DOOR_CLOSE_DELAY_SECONDS,
    DOOR_MOCK_MODE,
    YOLO_MODEL_PATH, YOLO_CONFIDENCE_THRESHOLD, YOLO_MAX_RETRIES,
    SENSOR_DATA_SEND_INTERVAL_SECONDS, TOKEN_VALIDATION_INTERVAL_HOURS,
    POLLING_INTERVAL_MS, SHARED_SENSORS_FILE
)


class FridgeDaemon:
    """
    Orchestratore principale che coordina tutti i componenti dello smart fridge.
    """
    
    def __init__(self):
        """Inizializza il daemon con tutti i componenti."""
        self.logger = get_logger('daemon')
        self.logger.info("=" * 60)
        self.logger.info("Smart Fridge Daemon - Initializing...")
        self.logger.info("=" * 60)
        
        # === INIZIALIZZA COMPONENTI ===
        
        # Server API
        self.api = ServerAPI(
            base_url=API_BASE_URL,
            token_file=FRIDGE_TOKEN_FILE,
            max_retries=API_MAX_RETRIES,
            retry_delay=API_RETRY_DELAY_SECONDS
        )
        
        # Camera manager
        self.camera = CameraManager(
            image_dir=CAMERA_IMAGE_DIR,
            max_retries=CAMERA_MAX_RETRIES
        )
        
        # Door sensor
        self.door = DoorSensor(
            gpio_pin=DOOR_GPIO_PIN,
            debounce_time=DOOR_DEBOUNCE_TIME_SECONDS,
            pull_up=DOOR_USE_PULLUP,
            mock_mode=DOOR_MOCK_MODE
        )
        
        # YOLO detector
        self.yolo = YOLODetector(
            model_path=YOLO_MODEL_PATH,
            confidence_threshold=YOLO_CONFIDENCE_THRESHOLD,
            max_retries=YOLO_MAX_RETRIES
        )
        
        # Sensori temperatura e potenza
        self.temp_sensor = TemperatureSensor()
        self.power_sensor = PowerSensor()
        
        # Data managers (per ora senza invio automatico al server)
        self.temp_data = DataManager('temperature', api_enabled=False)
        self.power_data = DataManager('power', api_enabled=False)
        
        # === STATO INTERNO ===
        
        # Buffer per dati da inviare al server ogni minuto
        self.temp_buffer: deque = deque()  # (timestamp, valore)
        self.power_buffer: deque = deque()
        
        # Timestamp ultimo invio dati e ultima validazione token
        self.last_sensor_send_time = datetime.utcnow()
        self.last_token_validation = None
        
        # Flag per controllo thread
        self.running = False
        self._sensor_thread = None
        self._door_thread = None
        
        self.logger.info("Daemon initialization complete")
    
    def initialize_components(self) -> bool:
        """
        Inizializza tutti i componenti hardware/software.
        
        Returns:
            bool: True se tutto ok, False se errori critici
        """
        self.logger.info("Initializing components...")
        
        success = True
        
        # === TOKEN VALIDATION ===
        if not self.api.is_configured():
            self.logger.warning("Fridge not configured (no token). Run setup procedure.")
            # Per ora continua lo stesso in modalitÃ  test
        else:
            self.logger.info("Fridge configured, validating token...")
            if self.api.should_validate_token():
                if self.api.validate_token():
                    self.last_token_validation = datetime.utcnow()
                else:
                    self.logger.error("Token validation failed!")
                    success = False
        
        # === CAMERA ===
        num_cameras = self.camera.discover_cameras()
        if num_cameras == 0:
            self.logger.error("No cameras found!")
            success = False
        else:
            if not self.camera.test_cameras():
                self.logger.warning("Some cameras failed test")
                success = False
        
        # === DOOR SENSOR ===
        if not self.door.initialize():
            self.logger.error("Door sensor initialization failed!")
            success = False
        
        # === YOLO ===
        if not self.yolo.initialize():
            self.logger.error("YOLO initialization failed!")
            #success = False                    TODO: RICORDATI DI SCOMMENTARE QUESTA RIGA QUANDO AVREMO YOLO
        else:
            # Log info modello
            model_info = self.yolo.get_model_info()
            self.logger.info(f"YOLO model loaded: {model_info.get('num_classes', 'N/A')} classes")
        
        # === SENSORI ===
        if not self.temp_sensor.initialize():
            self.logger.error("Temperature sensor initialization failed!")
            success = False
        
        if not self.power_sensor.initialize():
            self.logger.error("Power sensor initialization failed!")
            success = False
        
        if success:
            self.logger.info("All components initialized successfully!")
        else:
            self.logger.warning("Some components failed to initialize")
        
        return success
    
    # ============================================================
    # MAIN LOOP
    # ============================================================
    
    def start(self):
        """Avvia il daemon (blocking)."""
        self.logger.info("Starting daemon...")
        
        if not self.initialize_components():
            self.logger.error("Initialization failed, aborting")
            return
        
        self.running = True
        
        # === THREAD SENSORI (polling temp/power) ===
        self._sensor_thread = threading.Thread(target=self._sensor_polling_loop, daemon=True)
        self._sensor_thread.start()
        self.logger.info("Sensor polling thread started")
        
        # === THREAD DOOR MONITOR (con callback) ===
        self.door.set_on_door_closed_callback(self._on_door_closed)
        self.door.set_on_door_opened_callback(self._on_door_opened)
        
        self._door_thread = threading.Thread(target=self.door.monitor_loop, args=(0.5,), daemon=True)
        self._door_thread.start()
        self.logger.info("Door monitor thread started")
        
        # === MAIN LOOP (gestione token e monitoring) ===
        self.logger.info("Daemon running. Press Ctrl+C to stop.")
        try:
            while self.running:
                # Valida token se necessario
                self._check_token_validation()
                
                # Sleep per non consumare CPU
                time.sleep(10)
                
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        finally:
            self.stop()
    
    def stop(self):
        """Ferma il daemon e libera risorse."""
        self.logger.info("Stopping daemon...")
        self.running = False
        
        # Aspetta che i thread finiscano
        if self._sensor_thread:
            self._sensor_thread.join(timeout=2)
        if self._door_thread:
            self._door_thread.join(timeout=2)
        
        # Cleanup componenti
        self.camera.cleanup()
        self.door.cleanup()
        self.yolo.cleanup()
        self.temp_sensor.cleanup()
        self.power_sensor.cleanup()
        
        self.logger.info("Daemon stopped")
    
    # ============================================================
    # SENSOR POLLING
    # ============================================================
    
    def _sensor_polling_loop(self):
        """
        Loop polling sensori (temperatura e potenza).
        Legge ogni secondo e accumula per invio ogni minuto.
        """
        while self.running:
            try:
                # Leggi temperatura
                temp = self.temp_sensor.read()
                timestamp = datetime.utcnow()
                self.temp_buffer.append((timestamp.isoformat(), temp))
                self.temp_data.add_data_point(temp, timestamp)
                
                # Leggi potenza
                power = self.power_sensor.read()
                self.power_buffer.append((timestamp.isoformat(), power))
                self.power_data.add_data_point(power, timestamp)
                
                # Salva dati in file condiviso per UI
                self._save_sensors_to_file(temp, power, timestamp)
                
                # Invia al server se è passato 1 minuto
                self._check_sensor_data_send()
                
            except Exception as e:
                self.logger.error(f"Error in sensor polling: {e}")
                error_data = log_error_for_server('daemon', 'SensorPollingError', str(e))
                # Continua il loop anche in caso di errore
            
            # Aspetta intervallo polling
            time.sleep(POLLING_INTERVAL_MS / 1000.0)
    
    def _save_sensors_to_file(self, temperature: float, power: float, timestamp: datetime):
        """
        Salva i dati dei sensori in un file JSON condiviso per la UI.
        
        Args:
            temperature: Temperatura corrente (°C)
            power: Potenza corrente (W)
            timestamp: Timestamp della lettura
        """
        try:
            data = {
                "temperature": round(temperature, 2),
                "power": round(power, 2),
                "timestamp": timestamp.isoformat(),
                "last_update": datetime.now().isoformat()
            }
            
            # Scrivi atomicamente usando file temporaneo
            temp_file = Path(SHARED_SENSORS_FILE).with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Rinomina (operazione atomica)
            temp_file.replace(SHARED_SENSORS_FILE)
            
        except Exception as e:
            self.logger.error(f"Error saving sensors to file: {e}")
    
    def _check_sensor_data_send(self):
        """Invia dati sensori al server se Ã¨ passato l'intervallo configurato."""
        now = datetime.utcnow()
        elapsed = (now - self.last_sensor_send_time).total_seconds()
        
        if elapsed >= SENSOR_DATA_SEND_INTERVAL_SECONDS:
            self.logger.info("Sending sensor data to server...")
            
            # Converti buffer in liste
            temp_data_list = list(self.temp_buffer)
            power_data_list = list(self.power_buffer)
            
            if temp_data_list or power_data_list:
                success = self.api.send_sensor_data(temp_data_list, power_data_list)
                
                if success:
                    self.logger.info(f"Sent {len(temp_data_list)} temp and {len(power_data_list)} power readings")
                    # Svuota buffer dopo invio riuscito
                    self.temp_buffer.clear()
                    self.power_buffer.clear()
                    self.last_sensor_send_time = now
                else:
                    self.logger.error("Failed to send sensor data")
                    # Non svuota buffer, riproverÃ  al prossimo intervallo
            else:
                self.logger.debug("No sensor data to send")
                self.last_sensor_send_time = now
    
    # ============================================================
    # DOOR CALLBACKS
    # ============================================================
    
    def _on_door_opened(self):
        """Callback chiamata quando la porta si apre."""
        self.logger.info("Door opened")
        # Per ora non facciamo nulla quando la porta si apre
        # In futuro potremmo attivare una modalitÃ  di monitoraggio
    
    def _on_door_closed(self):
        """
        Callback chiamata quando la porta si chiude.
        Trigger: cattura foto â†’ detection YOLO â†’ invio prodotti al server.
        """
        self.logger.info("Door closed - starting capture sequence")
        
        try:
            # Attendi stabilizzazione dopo chiusura porta
            self.logger.info(f"Waiting {DOOR_CLOSE_DELAY_SECONDS}s for stabilization...")
            time.sleep(DOOR_CLOSE_DELAY_SECONDS)
            
            # === STEP 1: CATTURA FOTO ===
            self.logger.info("Capturing images from cameras...")
            image_paths = self.camera.capture_images(label="fridge")
            
            if not image_paths:
                self.logger.error("No images captured!")
                error_data = log_error_for_server(
                    'daemon',
                    'CaptureError',
                    'Failed to capture images after door closed'
                )
                # Invia errore al server
                if self.api.is_configured():
                    self.api.send_error_report(error_data)
                return
            
            self.logger.info(f"Captured {len(image_paths)} image(s)")
            
            # === STEP 2: YOLO DETECTION ===
            self.logger.info("Running YOLO detection...")
            products = self.yolo.detect_products_from_images(image_paths)
            
            if not products:
                self.logger.warning("No products detected")
                # Non Ã¨ necessariamente un errore (frigo potrebbe essere vuoto)
            else:
                self.logger.info(f"Detected {len(products)} unique product(s)")
            
            # === STEP 3: CREA JSON ===
            products_json = self.yolo.create_products_json(products)
            self.logger.debug(f"Products JSON: {products_json}")
            
            # === STEP 4: INVIA AL SERVER ===
            if self.api.is_configured():
                self.logger.info("Sending products to server...")
                success = self.api.send_products(products_json['prodotti'])
                
                if success:
                    self.logger.info("Products sent successfully")
                else:
                    self.logger.error("Failed to send products to server")
                    error_data = log_error_for_server(
                        'daemon',
                        'ServerSendError',
                        'Failed to send products to server after detection'
                    )
                    # L'errore Ã¨ giÃ  loggato, continua normalmente
            else:
                self.logger.warning("Fridge not configured, skipping server send")
            
            self.logger.info("Door closed sequence complete")
            
        except Exception as e:
            self.logger.error(f"Error in door closed sequence: {e}")
            error_data = log_error_for_server(
                'daemon',
                'DoorSequenceError',
                f'Unexpected error in door closed sequence: {str(e)}'
            )
            # Invia errore al server se configurato
            if self.api.is_configured():
                self.api.send_error_report(error_data)
    
    # ============================================================
    # TOKEN VALIDATION
    # ============================================================
    
    def _check_token_validation(self):
        """Valida il token se sono passate 24h."""
        if not self.api.is_configured():
            return
        
        if not self.last_token_validation:
            # Prima validazione
            if self.api.should_validate_token():
                self.logger.info("Running first token validation...")
                if self.api.validate_token():
                    self.last_token_validation = datetime.utcnow()
            return
        
        # Verifica se sono passate 24h
        elapsed = datetime.utcnow() - self.last_token_validation
        if elapsed > timedelta(hours=TOKEN_VALIDATION_INTERVAL_HOURS):
            self.logger.info("24h elapsed, validating token...")
            if self.api.validate_token():
                self.last_token_validation = datetime.utcnow()
                self.logger.info("Token validated successfully")
            else:
                self.logger.error("Token validation failed!")
                # Continua comunque, riproverÃ  piÃ¹ tardi


def main():
    """Entry point per fridge daemon."""
    daemon = FridgeDaemon()
    daemon.start()


if __name__ == "__main__":
    main()