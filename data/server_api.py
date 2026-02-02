"""
ServerAPI: gestisce tutte le comunicazioni con il server backend.
Responsabilità:
- Autenticazione e gestione token frigo
- Invio dati temperatura/consumi aggregati
- Invio lista prodotti riconosciuti
- Invio notifiche errori
- Retry automatico su failure
"""

import requests
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from logger.logger import get_logger


class ServerAPI:
    """
    Client API per comunicazione con server backend.
    Gestisce token, retry, e tutte le chiamate HTTP.
    """
    
    def __init__(self, base_url: str, token_file: str = "fridge_token.json", 
                 max_retries: int = 3, retry_delay: int = 5):
        """
        Inizializza il client API.
        
        Args:
            base_url: URL base del server (es. "https://api.smartfridge.com")
            token_file: Path del file dove salvare il token frigo
            max_retries: Numero massimo di retry su errore
            retry_delay: Secondi tra un retry e l'altro
        """
        self.base_url = base_url.rstrip('/')
        self.token_file = Path(token_file)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.logger = get_logger('server_api')
        
        # Token frigo (caricato da file se esiste)
        self.fridge_token: Optional[str] = None
        self.token_last_validated: Optional[datetime] = None
        
        self._load_token()
        
        self.logger.info(f"ServerAPI initialized (base_url: {self.base_url})")
    
    # ============================================================
    # TOKEN MANAGEMENT
    # ============================================================
    
    def _load_token(self) -> bool:
        """
        Carica il token frigo dal file locale.
        
        Returns:
            bool: True se token caricato, False se file non esiste
        """
        if not self.token_file.exists():
            self.logger.warning(f"Token file not found: {self.token_file}")
            return False
        
        try:
            with open(self.token_file, 'r') as f:
                data = json.load(f)
                self.fridge_token = data.get('token')
                
                # Carica timestamp ultima validazione se presente
                last_validated_str = data.get('last_validated')
                if last_validated_str:
                    self.token_last_validated = datetime.fromisoformat(last_validated_str)
            
            self.logger.info("Token loaded from file")
            return True
        except Exception as e:
            self.logger.error(f"Error loading token: {e}")
            return False
    
    def _save_token(self):
        """Salva il token frigo su file locale."""
        try:
            data = {
                'token': self.fridge_token,
                'last_validated': datetime.utcnow().isoformat() if self.token_last_validated else None
            }
            
            with open(self.token_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info("Token saved to file")
        except Exception as e:
            self.logger.error(f"Error saving token: {e}")
    
    def validate_token(self) -> bool:
        """
        Valida il token corrente chiamando /isAuthorized.
        Aggiorna il token se il server ne restituisce uno nuovo.
        
        Returns:
            bool: True se token valido, False altrimenti
        """
        if not self.fridge_token:
            self.logger.error("No token available for validation")
            return False
        
        try:
            url = f"{self.base_url}/isAuthorized"
            params = {'tokenFrigo': self.fridge_token}
            
            self.logger.info("Validating token...")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            new_token = data.get('token')
            
            if new_token and new_token != self.fridge_token:
                self.logger.info("Token renewed by server")
                self.fridge_token = new_token
            
            self.token_last_validated = datetime.utcnow()
            self._save_token()
            
            self.logger.info("Token validated successfully")
            return True
            
        except requests.RequestException as e:
            self.logger.error(f"Token validation failed: {e}")
            return False
    
    def should_validate_token(self) -> bool:
        """
        Verifica se è necessario validare il token.
        La validazione viene fatta una volta al giorno.
        
        Returns:
            bool: True se serve validazione, False altrimenti
        """
        if not self.token_last_validated:
            return True
        
        # Valida se sono passate 24 ore
        return datetime.utcnow() - self.token_last_validated > timedelta(days=1)
    
    def setup_fridge(self) -> bool:
        """
        Registra un nuovo frigo chiamando /setupFrigo.php.
        Salva il token ricevuto.
        
        NOTA: Questa funzione sarà chiamata dalla procedura di setup iniziale
        quando l'app del collega sarà pronta.
        
        Returns:
            bool: True se setup riuscito, False altrimenti
        """
        try:
            url = f"{self.base_url}/setupFrigo.php"
            
            self.logger.info("Setting up new fridge...")
            response = requests.post(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self.fridge_token = data.get('token')
            
            if not self.fridge_token:
                self.logger.error("Server did not return token")
                return False
            
            self.token_last_validated = datetime.utcnow()
            self._save_token()
            
            self.logger.info(f"Fridge setup complete (token: {self.fridge_token[:8]}...)")
            return True
            
        except requests.RequestException as e:
            self.logger.error(f"Fridge setup failed: {e}")
            return False
    
    # ============================================================
    # DATA SENDING
    # ============================================================
    
    def send_sensor_data(self, temperature_data: List[Tuple[str, float]], 
                        power_data: List[Tuple[str, float]]) -> bool:
        """
        Invia dati aggregati di temperatura e consumi al server (PUT request).
        Chiamato ogni minuto con i dati raccolti.
        
        Args:
            temperature_data: Lista di tuple (timestamp_iso, valore_celsius)
            power_data: Lista di tuple (timestamp_iso, valore_watt)
        
        Returns:
            bool: True se invio riuscito, False altrimenti
        """
        if not self.fridge_token:
            self.logger.error("Cannot send data: no token available")
            return False
        
        payload = {
            'token': self.fridge_token,
            'temperature': [
                {'timestamp': ts, 'value': val} 
                for ts, val in temperature_data
            ],
            'power': [
                {'timestamp': ts, 'value': val} 
                for ts, val in power_data
            ]
        }
        
        return self._send_with_retry(
            method='PUT',
            endpoint='/sensorData.php',  # Endpoint da confermare con collega
            json_data=payload,
            operation_name='send_sensor_data'
        )
    
    def send_products(self, products: List[Dict[str, any]]) -> bool:
        """
        Invia lista prodotti riconosciuti al server (POST request).
        Chiamato ogni volta che la porta del frigo si chiude.
        
        Args:
            products: Lista dizionari nel formato:
                      [{"nomeProdotto": "X", "marchio": "Y", "taglia": "Z", "quantita": N}, ...]
        
        Returns:
            bool: True se invio riuscito, False altrimenti
        """
        if not self.fridge_token:
            self.logger.error("Cannot send products: no token available")
            return False
        
        payload = {
            'token': self.fridge_token,
            'prodotti': products
        }
        
        return self._send_with_retry(
            method='POST',
            endpoint='/setProdotti.php',
            json_data=payload,
            operation_name='send_products'
        )
    
    def send_error_report(self, error_data: Dict) -> bool:
        """
        Invia report di errore al server per monitoraggio.
        
        Args:
            error_data: Dizionario con info errore (da log_error_for_server)
        
        Returns:
            bool: True se invio riuscito, False altrimenti
        """
        if not self.fridge_token:
            self.logger.warning("Cannot send error report: no token available")
            return False
        
        payload = {
            'token': self.fridge_token,
            'error': error_data
        }
        
        # Per errori non fare retry aggressivo (non è critico)
        return self._send_with_retry(
            method='POST',
            endpoint='/reportError.php',  # Endpoint da confermare
            json_data=payload,
            operation_name='send_error_report',
            max_retries=1  # Solo 1 retry per errori
        )
    
    # ============================================================
    # HTTP HELPERS
    # ============================================================
    
    def _send_with_retry(self, method: str, endpoint: str, json_data: Dict,
                        operation_name: str, max_retries: int = None) -> bool:
        """
        Invia richiesta HTTP con retry automatico su fallimento.
        
        Args:
            method: Metodo HTTP ('GET', 'POST', 'PUT')
            endpoint: Endpoint API (es. '/setProdotti.php')
            json_data: Payload JSON da inviare
            operation_name: Nome operazione per logging
            max_retries: Override del numero massimo di retry
        
        Returns:
            bool: True se richiesta riuscita, False dopo tutti i retry
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"{operation_name}: attempt {attempt + 1}/{max_retries + 1}")
                
                # Invia richiesta
                if method == 'GET':
                    response = requests.get(url, params=json_data, timeout=10)
                elif method == 'POST':
                    response = requests.post(url, json=json_data, timeout=10)
                elif method == 'PUT':
                    response = requests.put(url, json=json_data, timeout=10)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                
                self.logger.info(f"{operation_name}: success")
                return True
                
            except requests.RequestException as e:
                self.logger.warning(f"{operation_name} failed (attempt {attempt + 1}): {e}")
                
                # Se non è l'ultimo tentativo, aspetta prima di ritentare
                if attempt < max_retries:
                    import time
                    time.sleep(self.retry_delay)
        
        self.logger.error(f"{operation_name}: all retries exhausted")
        return False
    
    # ============================================================
    # UTILITY
    # ============================================================
    
    def is_configured(self) -> bool:
        """
        Verifica se il frigo è configurato (ha un token valido).
        
        Returns:
            bool: True se configurato, False altrimenti
        """
        return self.fridge_token is not None
    
    def get_token(self) -> Optional[str]:
        """
        Ritorna il token frigo corrente.
        
        Returns:
            Optional[str]: Token o None se non configurato
        """
        return self.fridge_token