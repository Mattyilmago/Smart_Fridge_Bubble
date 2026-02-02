"""
Sensore di consumo elettrico (Wattmetro).
Versione MOCK: genera dati casuali per sviluppo.
TODO: Sostituire con lettura reale quando disponibile hardware.
"""

import random
import time
from .abstract_sensor import AbstractSensor
from config import POWER_RANGE

class PowerSensor(AbstractSensor):
    """
    Sensore di consumo energetico del frigo.
    Attualmente genera valori mock, ma mantiene l'interfaccia per sensore reale.
    """
    
    def __init__(self):
        super().__init__(name="Power", unit="W")
        self._is_initialized = False
        
        # Parametri per simulazione realistica
        self._base_power = sum(POWER_RANGE) / 2  # Consumo medio
        self._variation = 5.0  # Variazione massima per step
        
        # Simulazione cicli compressore (opzionale)
        self._cycle_counter = 0
        self._cycle_active = False
    
    def initialize(self) -> bool:
        """
        Inizializza il wattmetro.
        MOCK: simula inizializzazione con delay.
        REAL: qui andrebbe il setup comunicazione con wattmetro.
        """
        print(f"[{self.name}] Initializing power meter...")
        time.sleep(0.1)  # Simula tempo di inizializzazione
        
        self._is_initialized = True
        self._last_value = self._base_power
        
        print(f"[{self.name}] Power meter initialized successfully")
        return True
    
    def read(self) -> float:
        """
        Legge il consumo energetico corrente.
        MOCK: genera valore casuale simulando cicli del compressore.
        REAL: qui andrebbe la lettura dal wattmetro reale.
        
        Returns:
            float: Potenza consumata in Watt
        """
        if not self._is_initialized:
            raise RuntimeError(f"{self.name} sensor not initialized. Call initialize() first.")
        
        # === SIMULAZIONE MOCK ===
        # Simula cicli on/off del compressore (ogni ~60 letture cambia stato)
        self._cycle_counter += 1
        if self._cycle_counter > 60:
            self._cycle_active = not self._cycle_active
            self._cycle_counter = 0
        
        # Consumo più alto quando compressore attivo
        if self._cycle_active:
            target = POWER_RANGE[1] * 0.8  # 80% del massimo quando attivo
        else:
            target = POWER_RANGE[0] * 1.2  # 20% sopra il minimo quando inattivo
        
        # Variazione graduale verso target
        change = (target - self._last_value) * 0.1 + random.uniform(-self._variation, self._variation)
        new_value = self._last_value + change
        
        # Mantieni nei limiti
        min_power, max_power = POWER_RANGE
        new_value = max(min_power, min(max_power, new_value))
        
        self._last_value = new_value
        
        # === CODICE PER WATTMETRO REALE (esempio generico) ===
        # Decommenta e adatta al tuo wattmetro specifico
        """
        try:
            # Esempio: lettura da modulo I2C o seriale
            # self._last_value = self.wattmeter_device.read_power()
            
            # Oppure lettura da GPIO con conversione ADC
            # raw_value = self.adc.read_channel(self.channel)
            # self._last_value = self._convert_to_watts(raw_value)
            
            pass
        except Exception as e:
            print(f"Error reading power sensor: {e}")
            # Usa ultimo valore valido
        """
        
        return self._last_value
    
    def cleanup(self):
        """
        Cleanup risorse del wattmetro.
        MOCK: nessuna risorsa da liberare.
        REAL: qui andrebbe il cleanup connessioni/GPIO.
        """
        print(f"[{self.name}] Power meter cleanup completed")
        self._is_initialized = False