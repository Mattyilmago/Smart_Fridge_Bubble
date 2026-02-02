"""
Sensore di temperatura.
"""

import board
import adafruit_bmp280
from .abstract_sensor import AbstractSensor


class TemperatureSensor(AbstractSensor):
    """
    Sensore di temperatura del frigo.
    """
    
    def __init__(self):
        super().__init__(name="Temperature", unit="°C")
        self._is_initialized = False


    def initialize(self) -> bool:
        """
        Inizializza il sensore.
        qui andrebbe il setup GPIO/I2C.
        """
        try:
            i2c = board.I2C()
            # Il sensore BMP280 può essere all'indirizzo 0x76 o 0x77
            # Specifica esplicitamente 0x76 se quello è il tuo indirizzo
            self.sensor = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)
            self._is_initialized = True
            return True
        except Exception as e:
            print(f"[TemperatureSensor] Errore inizializzazione: {e}")
            self._is_initialized = False
            return False
    
    def read(self) -> float:
        """
        Legge la temperatura corrente.
        qui andrebbe la lettura GPIO/I2C reale.
        
        Returns:
            float: Temperatura in °C
        """
        if not self._is_initialized:
            raise RuntimeError(f"{self.name} sensor not initialized. Call initialize() first.")
        
        temp = self.sensor.temperature
        print(f"[TemperatureSensor] Read: {temp:.2f}°C")
        return temp



    
    def cleanup(self):
        """
        Cleanup risorse del sensore.
        qui andrebbe il cleanup GPIO se necessario.
        """
        self.sensor = None
        self._is_initialized = False