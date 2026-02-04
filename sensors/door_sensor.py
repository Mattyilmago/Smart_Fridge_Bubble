"""
DoorSensor: gestisce il reed switch per rilevare apertura/chiusura porta frigo.
Responsabilità:
- Lettura stato GPIO reed switch
- Debouncing per evitare falsi positivi
- Callback su eventi apertura/chiusura
- Mock mode con input manuale per testing remoto
"""

import time
from typing import Optional, Callable
from enum import Enum
import sys
from pathlib import Path

from logger.logger import get_logger

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO_AVAILABLE = False


class DoorState(Enum):
    """Stati possibili della porta."""
    OPEN = "open"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class DoorSensor:
    """
    Gestisce il reed switch per rilevare apertura/chiusura porta frigo.
    
    Reed switch tipico:
    - Normalmente Aperto (NO): circuito aperto quando magnete lontano, chiuso quando vicino
    - Porta CHIUSA = magnete vicino = GPIO LOW
    - Porta APERTA = magnete lontano = GPIO HIGH
    """
    
    def __init__(self, gpio_pin: int = 17, 
                 debounce_time: float = 0.1,
                 pull_up: bool = True,
                 mock_mode: bool = False):
        """
        Inizializza il sensore porta.
        
        Args:
            gpio_pin: Pin GPIO a cui è collegato il reed switch (default: GPIO17)
            debounce_time: Tempo di debouncing in secondi (default: 0.1s = 100ms)
            pull_up: Se True usa pull-up interno (GPIO HIGH quando aperto)
            mock_mode: Se True, usa input manuale invece di GPIO (per testing remoto via SSH)
        """
        self.gpio_pin = gpio_pin
        self.debounce_time = debounce_time
        self.pull_up = pull_up
        self.mock_mode = mock_mode or not GPIO_AVAILABLE
        
        self.logger = get_logger('door_sensor')
        
        # Stato corrente della porta
        self._current_state = DoorState.UNKNOWN
        self._last_change_time: Optional[float] = None
        
        # Callback per eventi
        self._on_door_closed: Optional[Callable] = None
        self._on_door_opened: Optional[Callable] = None
        
        self._is_initialized = False
        
        if self.mock_mode:
            self.logger.warning("DoorSensor running in MOCK mode (manual input via SSH)")
        elif not GPIO_AVAILABLE:
            self.logger.warning("RPi.GPIO not available - forcing MOCK mode")
            self.mock_mode = True
        else:
            self.logger.info(f"DoorSensor initialized (GPIO pin: {gpio_pin})")
    
    def initialize(self) -> bool:
        """
        Inizializza il GPIO per il reed switch.
        
        Returns:
            bool: True se inizializzazione riuscita, False altrimenti
        """
        if self.mock_mode:
            self.logger.info("MOCK mode - no GPIO initialization needed")
            self._is_initialized = True
            self._current_state = DoorState.CLOSED  # Assume porta chiusa in mock
            return True
        
        try:
            # Setup GPIO mode
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Configura pin come input con pull-up/down
            if self.pull_up:
                GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            else:
                GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            
            # Leggi stato iniziale
            self._update_state()
            
            self._is_initialized = True
            self.logger.info(f"GPIO initialized - initial state: {self._current_state.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize GPIO: {e}")
            return False
    
    def _update_state(self):
        """Aggiorna lo stato corrente leggendo il GPIO."""
        if self.mock_mode:
            return
        
        # Leggi GPIO
        gpio_value = GPIO.input(self.gpio_pin)
        
        # Con pull-up: LOW = porta chiusa, HIGH = porta aperta
        # Con pull-down: HIGH = porta chiusa, LOW = porta aperta
        if self.pull_up:
            new_state = DoorState.CLOSED if gpio_value == GPIO.LOW else DoorState.OPEN
        else:
            new_state = DoorState.OPEN if gpio_value == GPIO.LOW else DoorState.CLOSED
        
        # Aggiorna solo se stato è cambiato
        if new_state != self._current_state:
            self._current_state = new_state
            self._last_change_time = time.time()
            self.logger.info(f"Door state changed: {new_state.value}")
    
    def get_state(self) -> DoorState:
        """
        Ritorna lo stato corrente della porta.
        
        Returns:
            DoorState: Stato corrente (OPEN, CLOSED, UNKNOWN)
        """
        if not self._is_initialized:
            self.logger.warning("Sensor not initialized")
            return DoorState.UNKNOWN
        
        if not self.mock_mode:
            self._update_state()
        
        return self._current_state
    
    def is_door_closed(self) -> bool:
        """
        Verifica se la porta è chiusa.
        
        Returns:
            bool: True se porta chiusa, False altrimenti
        """
        return self.get_state() == DoorState.CLOSED
    
    def is_door_open(self) -> bool:
        """
        Verifica se la porta è aperta.
        
        Returns:
            bool: True se porta aperta, False altrimenti
        """
        return self.get_state() == DoorState.OPEN
    
    def set_on_door_closed_callback(self, callback: Callable):
        """
        Imposta callback chiamata quando la porta si chiude.
        
        Args:
            callback: Funzione da chiamare (no arguments)
        """
        self._on_door_closed = callback
        self.logger.info("Door closed callback registered")
    
    def set_on_door_opened_callback(self, callback: Callable):
        """
        Imposta callback chiamata quando la porta si apre.
        
        Args:
            callback: Funzione da chiamare (no arguments)
        """
        self._on_door_opened = callback
        self.logger.info("Door opened callback registered")
    
    def monitor_loop(self, check_interval: float = 0.5):
        """
        Loop di monitoraggio continuo con callback su cambio stato.
        BLOCKING - da usare in thread separato.
        
        In MOCK mode: aspetta input ENTER dall'utente per simulare chiusura porta.
        In HARDWARE mode: polling GPIO continuo.
        
        Args:
            check_interval: Intervallo tra controlli in secondi (solo hardware mode)
        """
        if not self._is_initialized:
            self.logger.error("Sensor not initialized, call initialize() first")
            return
        
        if self.mock_mode:
            self._mock_monitor_loop()
        else:
            self._hardware_monitor_loop(check_interval)
    
    def _mock_monitor_loop(self):
        """Loop MOCK: monitora file trigger per simulare chiusura porta."""
        self.logger.info("=" * 60)
        self.logger.info("MOCK MODE - Door Sensor")
        self.logger.info("=" * 60)
        self.logger.info("Monitoring trigger file: /tmp/fridge_door_trigger")
        self.logger.info("To trigger door close, run:")
        self.logger.info("  touch /tmp/fridge_door_trigger")
        self.logger.info("=" * 60)
        
        trigger_file = Path("/tmp/fridge_door_trigger")
        
        try:
            while True:
                # Controlla se esiste il file trigger
                if trigger_file.exists():
                    self.logger.info("=" * 60)
                    self.logger.info("🚪 Door CLOSING detected (trigger file)")
                    self.logger.info("=" * 60)
                    
                    # Rimuovi il file trigger
                    trigger_file.unlink()
                    
                    # Aggiorna stato interno
                    self._current_state = DoorState.CLOSED
                    self._last_change_time = time.time()
                    
                    # Trigger callback chiusura porta
                    if self._on_door_closed:
                        self._on_door_closed()
                    else:
                        self.logger.warning("No callback registered for door closed event")
                    
                    self.logger.info("=" * 60)
                    self.logger.info("Ready for next trigger...")
                    self.logger.info("=" * 60)
                
                time.sleep(0.5)  # Controlla ogni 500ms
                
        except KeyboardInterrupt:
            self.logger.info("\nMock monitor loop interrupted by user (Ctrl+C)")
    
    def _hardware_monitor_loop(self, check_interval: float):
        """Loop HARDWARE: polling GPIO con debouncing e callback."""
        self.logger.info("Starting hardware door monitor loop...")
        
        previous_state = self.get_state()
        
        try:
            while True:
                current_state = self.get_state()
                
                # Rileva transizioni di stato
                if current_state != previous_state:
                    # Debouncing: conferma che stato sia stabile
                    time.sleep(self.debounce_time)
                    confirmed_state = self.get_state()
                    
                    if confirmed_state == current_state:
                        # Stato confermato dopo debouncing
                        if confirmed_state == DoorState.CLOSED and self._on_door_closed:
                            self.logger.info("Door closed - triggering callback")
                            self._on_door_closed()
                        elif confirmed_state == DoorState.OPEN and self._on_door_opened:
                            self.logger.info("Door opened - triggering callback")
                            self._on_door_opened()
                        
                        previous_state = confirmed_state
                
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Hardware monitor loop interrupted by user")
    
    def cleanup(self):
        """Libera risorse GPIO."""
        if not self.mock_mode and GPIO_AVAILABLE and self._is_initialized:
            try:
                GPIO.cleanup(self.gpio_pin)
                self.logger.info("GPIO cleanup complete")
            except Exception as e:
                self.logger.error(f"Error during GPIO cleanup: {e}")
        
        self._is_initialized = False
    
    # ============================================================
    # FUNZIONI MOCK AGGIUNTIVE (per testing programmatico)
    # ============================================================
    
    def simulate_door_close(self):
        """MOCK: Simula chiusura porta (solo per testing programmatico)."""
        if not self.mock_mode:
            self.logger.warning("simulate_door_close() called without mock_mode - ignoring")
            return
        
        self.logger.info("MOCK: Simulating door close")
        self._current_state = DoorState.CLOSED
        self._last_change_time = time.time()
        
        if self._on_door_closed:
            self._on_door_closed()
    
    def simulate_door_open(self):
        """MOCK: Simula apertura porta (solo per testing programmatico)."""
        if not self.mock_mode:
            self.logger.warning("simulate_door_open() called without mock_mode - ignoring")
            return
        
        self.logger.info("MOCK: Simulating door open")
        self._current_state = DoorState.OPEN
        self._last_change_time = time.time()
        
        if self._on_door_opened:
            self._on_door_opened()