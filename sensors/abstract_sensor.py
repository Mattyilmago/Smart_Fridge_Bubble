"""
Classe base astratta per tutti i sensori.
Definisce l'interfaccia comune che ogni sensore deve implementare.
"""

from abc import ABC, abstractmethod
from typing import Optional

class AbstractSensor(ABC):
    """
    Classe astratta che definisce l'interfaccia per i sensori.
    Ogni sensore concreto deve implementare i metodi astratti.
    """
    
    def __init__(self, name: str, unit: str):
        """
        Inizializza il sensore.
        
        Args:
            name: Nome descrittivo del sensore (es. "Temperature")
            unit: Unità di misura (es. "°C", "W")
        """
        self.name = name
        self.unit = unit
        self._last_value: Optional[float] = None
    
    @abstractmethod
    def read(self) -> float:
        """
        Legge il valore corrente dal sensore.
        Questo metodo DEVE essere implementato da ogni sensore concreto.
        
        Returns:
            float: Valore letto dal sensore
        """
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Inizializza il sensore (es. setup GPIO, connessione I2C, etc.).
        
        Returns:
            bool: True se inizializzazione riuscita, False altrimenti
        """
        pass
    
    @abstractmethod
    def cleanup(self):
        """
        Libera le risorse del sensore (chiude connessioni, GPIO, etc.).
        Chiamato alla chiusura dell'applicazione.
        """
        pass
    
    def get_last_value(self) -> Optional[float]:
        """
        Ritorna l'ultimo valore letto senza fare una nuova lettura.
        
        Returns:
            Optional[float]: Ultimo valore o None se non ancora letto
        """
        return self._last_value
    
    def __str__(self) -> str:
        return f"{self.name} Sensor"