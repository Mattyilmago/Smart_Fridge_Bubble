"""
Shared Sensors: wrapper per leggere dati sensori dal file condiviso.
Il daemon scrive i dati, la UI li legge.
"""

import json
from pathlib import Path
from typing import Tuple
from config import SHARED_SENSORS_FILE


class SharedSensorReader:
    """Legge i dati dei sensori dal file condiviso scritto dal daemon."""
    
    def __init__(self):
        self.file_path = Path(SHARED_SENSORS_FILE)
        self._last_temperature = 5.0
        self._last_power = 100.0
    
    def read_sensors(self) -> Tuple[float, float]:
        """Legge temperatura e potenza dal file."""
        try:
            if not self.file_path.exists():
                return self._last_temperature, self._last_power
            
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            temp = data.get('temperature', self._last_temperature)
            power = data.get('power', self._last_power)
            
            self._last_temperature = temp
            self._last_power = power
            
            return temp, power
            
        except Exception:
            return self._last_temperature, self._last_power
    
    def get_temperature(self) -> float:
        """Legge solo temperatura."""
        temp, _ = self.read_sensors()
        return temp
    
    def get_power(self) -> float:
        """Legge solo potenza."""
        _, power = self.read_sensors()
        return power


class SharedTemperatureSensor:
    """Wrapper che simula TemperatureSensor ma legge dal file condiviso."""
    
    def __init__(self):
        self.reader = SharedSensorReader()
        self.name = "Temperature (Shared)"
        self.unit = "°C"
    
    def initialize(self) -> bool:
        return True
    
    def read(self) -> float:
        return self.reader.get_temperature()
    
    def cleanup(self):
        pass


class SharedPowerSensor:
    """Wrapper che simula PowerSensor ma legge dal file condiviso."""
    
    def __init__(self):
        self.reader = SharedSensorReader()
        self.name = "Power (Shared)"
        self.unit = "W"
    
    def initialize(self) -> bool:
        return True
    
    def read(self) -> float:
        return self.reader.get_power()
    
    def cleanup(self):
        pass