"""
DoorSensor: gestisce il reed switch per rilevare apertura/chiusura porta frigo.
Responsabilità:
- Lettura stato GPIO reed switch
- Debouncing per evitare falsi positivi
- Callback su eventi apertura/chiusura
- Gestione edge detection
"""

import time
from typing import Optional, Callable
from enum import Enum
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
                 pull_up: bool = True):
        """
        Inizializza il sensore porta.
        
        Args:
            gpio_pin: Pin GPIO a cui è collegato il reed switch (default: GPIO17)
            debounce_time: Tempo di debouncing in secondi (default: 0.1s = 100ms)
            pull_up: Se True usa pull-up interno (GPIO HIGH quando aperto)
        """
        self.gpio_pin = gpio_pin
        self.debounce_time = debounce_time
        self.pull_up = pull_up
        
        self.logger = get_logger('door_sensor')
        
        # Stato corrente della porta
        self._current_state = DoorState.UNKNOWN
        self._last_change_time: Optional[float] = None
        
        # Callback per eventi
        self._on_door_closed: Optional[Callable] = None
        self._on_door_opened: Optional[Callable] = None
        
        self._is_initialized = False
        
        if not GPIO_AVAILABLE:
            self.logger.warning("RPi.GPIO not available - running in MOCK mode")
        else:
            self.logger.info(f"DoorSensor initialized (GPIO pin: {gpio_pin})")
    
    def initialize(self) -> bool:
        """
        Inizializza il GPIO per il reed switch.
        
        Returns:
            bool: True se inizializzazione riuscita, False altrimenti
        """
        if not GPIO_AVAILABLE:
            self.logger.warning("GPIO not available - skipping hardware initialization")
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
        if not GPIO_AVAILABLE:
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
    
    def wait_for_door_closed(self, timeout: Optional[float] = None,
                            check_interval: float = 0.1) -> bool:
        """
        Attende che la porta si chiuda.
        
        Args:
            timeout: Timeout in secondi (None = attesa infinita)
            check_interval: Intervallo tra controlli in secondi
        
        Returns:
            bool: True se porta si è chiusa, False se timeout
        """
        self.logger.info("Waiting for door to close...")
        start_time = time.time()
        
        while True:
            if self.is_door_closed():
                # Applica debouncing: aspetta che lo stato rimanga stabile
                time.sleep(self.debounce_time)
                if self.is_door_closed():
                    self.logger.info("Door closed detected")
                    return True
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                self.logger.warning(f"Timeout waiting for door to close ({timeout}s)")
                return False
            
            time.sleep(check_interval)
    
    def wait_for_door_opened(self, timeout: Optional[float] = None,
                            check_interval: float = 0.1) -> bool:
        """
        Attende che la porta si apra.
        
        Args:
            timeout: Timeout in secondi (None = attesa infinita)
            check_interval: Intervallo tra controlli in secondi
        
        Returns:
            bool: True se porta si è aperta, False se timeout
        """
        self.logger.info("Waiting for door to open...")
        start_time = time.time()
        
        while True:
            if self.is_door_open():
                # Applica debouncing
                time.sleep(self.debounce_time)
                if self.is_door_open():
                    self.logger.info("Door opened detected")
                    return True
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                self.logger.warning(f"Timeout waiting for door to open ({timeout}s)")
                return False
            
            time.sleep(check_interval)
    
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
        
        Args:
            check_interval: Intervallo tra controlli in secondi
        """
        self.logger.info("Starting door monitor loop...")
        
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
            self.logger.info("Monitor loop interrupted by user")
    
    def cleanup(self):
        """Libera risorse GPIO."""
        if GPIO_AVAILABLE and self._is_initialized:
            try:
                GPIO.cleanup(self.gpio_pin)
                self.logger.info("GPIO cleanup complete")
            except Exception as e:
                self.logger.error(f"Error during GPIO cleanup: {e}")
        
        self._is_initialized = False
    
    # ============================================================
    # MOCK MODE (per testing senza hardware)
    # ============================================================
    
    def simulate_door_close(self):
        """MOCK: Simula chiusura porta (solo per testing)."""
        if GPIO_AVAILABLE:
            self.logger.warning("simulate_door_close() called with real GPIO - ignoring")
            return
        
        self.logger.info("MOCK: Simulating door close")
        self._current_state = DoorState.CLOSED
        self._last_change_time = time.time()
        
        if self._on_door_closed:
            self._on_door_closed()
    
    def simulate_door_open(self):
        """MOCK: Simula apertura porta (solo per testing)."""
        if GPIO_AVAILABLE:
            self.logger.warning("simulate_door_open() called with real GPIO - ignoring")
            return
        
        self.logger.info("MOCK: Simulating door open")
        self._current_state = DoorState.OPEN
        self._last_change_time = time.time()
        
        if self._on_door_opened:
            self._on_door_opened()