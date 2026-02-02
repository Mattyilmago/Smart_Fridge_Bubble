"""
DataManager: gestisce lo storico dati e la comunicazione con il server.
Responsabilità:
- Mantiene buffer locale degli ultimi 48h di dati
- Recupera storico iniziale da API server
- Invia nuove letture al server
- Calcola statistiche (media, min, max)
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import deque
import requests
from config import API_BASE_URL, API_ENDPOINTS, HISTORY_HOURS, MAX_DATA_POINTS


class DataPoint:
    """Rappresenta un singolo punto dati con timestamp."""
    
    def __init__(self, timestamp: datetime, value: float):
        self.timestamp = timestamp
        self.value = value
    
    def to_dict(self) -> dict:
        """Converte in dizionario per serializzazione JSON."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'value': self.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DataPoint':
        """Crea DataPoint da dizionario JSON."""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            value=float(data['value'])
        )


class DataManager:
    """
    Gestisce lo storico dati per temperatura e potenza.
    Mantiene buffer in memoria e sincronizza con server via API.
    """
    
    def __init__(self, sensor_type: str, api_enabled: bool = False):
        """
        Inizializza il DataManager.
        
        Args:
            sensor_type: Tipo sensore ("temperature" o "power")
            api_enabled: Se True, abilita comunicazione con API server
        """
        self.sensor_type = sensor_type
        self.api_enabled = api_enabled
        
        # Buffer circolare per dati (deque è efficiente per append/pop)
        self._data_buffer: deque[DataPoint] = deque(maxlen=MAX_DATA_POINTS)
        
        # Timestamp ultimo invio a server (per evitare invii troppo frequenti)
        self._last_server_sync = None
        self._sync_interval = timedelta(seconds=60)  # Invia al server ogni 60s
        
        print(f"[DataManager-{sensor_type}] Initialized")
    
    def load_history_from_server(self) -> bool:
        """
        Carica lo storico delle ultime 48h dal server via API.
        
        Returns:
            bool: True se caricamento riuscito, False altrimenti
        """
        if not self.api_enabled:
            print(f"[DataManager-{self.sensor_type}] API disabled, skipping history load")
            return False
        
        try:
            # Costruisci URL endpoint
            endpoint = API_ENDPOINTS[f'{self.sensor_type}_history']
            url = f"{API_BASE_URL}{endpoint}"
            
            # Parametri query: richiedi ultime 48h
            params = {
                'hours': HISTORY_HOURS
            }
            
            print(f"[DataManager-{self.sensor_type}] Fetching history from {url}...")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            
            # Converti in DataPoint e aggiungi a buffer
            for item in data.get('data', []):
                point = DataPoint.from_dict(item)
                self._data_buffer.append(point)
            
            print(f"[DataManager-{self.sensor_type}] Loaded {len(self._data_buffer)} historical points")
            return True
            
        except requests.RequestException as e:
            print(f"[DataManager-{self.sensor_type}] Error loading history: {e}")
            return False
        except Exception as e:
            print(f"[DataManager-{self.sensor_type}] Unexpected error: {e}")
            return False
    
    def add_data_point(self, value: float, timestamp: Optional[datetime] = None):
        """
        Aggiunge un nuovo punto dati al buffer locale.
        
        Args:
            value: Valore letto dal sensore
            timestamp: Timestamp del dato (default: now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        point = DataPoint(timestamp, value)
        self._data_buffer.append(point)
        
        # Rimuovi dati più vecchi di HISTORY_HOURS
        self._remove_old_data()
        
        # Invia al server se è passato abbastanza tempo dall'ultimo sync
        if self.api_enabled:
            self._sync_to_server_if_needed(point)
    
    def _remove_old_data(self):
        """
        Rimuove i dati più vecchi di HISTORY_HOURS dal buffer.
        Questo assicura che vengano visualizzate solo le ultime 48 ore.
        """
        if not self._data_buffer:
            return
        
        cutoff_time = datetime.now() - timedelta(hours=HISTORY_HOURS)
        
        # Rimuovi i punti troppo vecchi dall'inizio del deque
        while self._data_buffer and self._data_buffer[0].timestamp < cutoff_time:
            self._data_buffer.popleft()
    
    def _sync_to_server_if_needed(self, point: DataPoint):
        """
        Invia il dato al server se è passato l'intervallo di sync.
        Evita di sovraccaricare il server con troppi POST.
        """
        now = datetime.now()
        
        # Prima sincronizzazione o intervallo trascorso
        if (self._last_server_sync is None or 
            now - self._last_server_sync >= self._sync_interval):
            
            self._send_to_server(point)
            self._last_server_sync = now
    
    def _send_to_server(self, point: DataPoint):
        """
        Invia un singolo punto dati al server via POST.
        """
        try:
            endpoint = API_ENDPOINTS[f'{self.sensor_type}_post']
            url = f"{API_BASE_URL}{endpoint}"
            
            payload = point.to_dict()
            
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            
            # print(f"[DataManager-{self.sensor_type}] Data sent to server")
            
        except requests.RequestException as e:
            print(f"[DataManager-{self.sensor_type}] Error sending data: {e}")
    
    def get_data_points(self, hours: Optional[int] = None) -> List[DataPoint]:
        """
        Ritorna i punti dati del periodo richiesto.
        
        Args:
            hours: Numero di ore indietro (None = tutti i dati disponibili)
        
        Returns:
            List[DataPoint]: Lista di punti dati ordinati cronologicamente
        """
        if hours is None:
            return list(self._data_buffer)
        
        # Filtra solo dati nelle ultime N ore
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [p for p in self._data_buffer if p.timestamp >= cutoff_time]
    
    def get_statistics(self, hours: Optional[int] = None) -> Dict[str, float]:
        """
        Calcola statistiche sui dati del periodo specificato.
        
        Args:
            hours: Numero di ore indietro (None = tutti i dati)
        
        Returns:
            Dict con keys: 'average', 'min', 'max', 'count'
        """
        data_points = self.get_data_points(hours)
        
        if not data_points:
            return {
                'average': 0.0,
                'min': 0.0,
                'max': 0.0,
                'count': 0
            }
        
        values = [p.value for p in data_points]
        
        return {
            'average': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'count': len(values)
        }
    
    def get_average(self, hours: Optional[int] = None) -> float:
        """
        Ritorna la media dei valori nel periodo specificato.
        
        Args:
            hours: Numero di ore indietro (None = tutti i dati)
        
        Returns:
            float: Valore medio
        """
        return self.get_statistics(hours)['average']
    
    def get_latest_value(self) -> Optional[float]:
        """
        Ritorna l'ultimo valore registrato.
        
        Returns:
            Optional[float]: Ultimo valore o None se buffer vuoto
        """
        if not self._data_buffer:
            return None
        return self._data_buffer[-1].value
    
    def clear(self):
        """Svuota il buffer dati."""
        self._data_buffer.clear()
        print(f"[DataManager-{self.sensor_type}] Buffer cleared")