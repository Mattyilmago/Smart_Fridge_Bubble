"""
Logger centralizzato per Smart Fridge.
Gestisce logging su file con rotazione automatica e output console.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path


class FridgeLogger:
    """
    Logger centralizzato con supporto per:
    - File logging con rotazione automatica
    - Console output colorato (opzionale)
    - Livelli di log configurabili per modulo
    """
    
    _loggers = {}  # Cache dei logger per modulo
    
    @classmethod
    def get_logger(cls, module_name: str, log_level: int = logging.INFO) -> logging.Logger:
        """
        Ottiene o crea un logger per il modulo specificato.
        
        Args:
            module_name: Nome del modulo (es. "camera", "yolo", "api")
            log_level: Livello minimo di logging (default: INFO)
        
        Returns:
            logging.Logger: Logger configurato per il modulo
        """
        # Ritorna logger cached se esiste
        if module_name in cls._loggers:
            return cls._loggers[module_name]
        
        # Crea nuovo logger
        logger = logging.getLogger(f"SmartFridge.{module_name}")
        logger.setLevel(log_level)
        
        # Evita duplicazione handler se logger già configurato
        if logger.handlers:
            cls._loggers[module_name] = logger
            return logger
        
        # === FILE HANDLER con rotazione ===
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / "fridge_errors.log"
        
        # RotatingFileHandler: max 10MB per file, mantiene 5 backup
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.WARNING)  # File solo per WARNING+
        
        # Formato file: timestamp completo + modulo + livello + messaggio
        file_formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # === CONSOLE HANDLER ===
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)  # Console mostra tutto
        
        # Formato console: più compatto
        console_formatter = logging.Formatter(
            '[%(name)s] %(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # Aggiungi handlers al logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Salva in cache
        cls._loggers[module_name] = logger
        
        return logger
    
    @classmethod
    def log_error_to_server(cls, module: str, error_type: str, error_message: str, 
                           traceback_info: str = None):
        """
        Helper per loggare errori critici che devono essere inviati al server.
        Crea un dizionario strutturato pronto per essere inviato via API.
        
        Args:
            module: Nome modulo che ha generato l'errore
            error_type: Tipo di errore (es. "CameraError", "YOLOError")
            error_message: Messaggio di errore
            traceback_info: Traceback completo (opzionale)
        
        Returns:
            dict: Dizionario con info errore pronto per invio server
        """
        error_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'module': module,
            'error_type': error_type,
            'message': error_message,
            'traceback': traceback_info
        }
        
        # Log locale
        logger = cls.get_logger(module)
        logger.error(f"{error_type}: {error_message}")
        if traceback_info:
            logger.debug(f"Traceback: {traceback_info}")
        
        return error_data


# Funzioni di convenienza per uso rapido
def get_logger(module_name: str, log_level: int = logging.INFO) -> logging.Logger:
    """
    Shortcut per ottenere logger.
    
    Usage:
        from utils.logger import get_logger
        logger = get_logger('camera')
        logger.info("Camera initialized")
    """
    return FridgeLogger.get_logger(module_name, log_level)


def log_error_for_server(module: str, error_type: str, message: str, 
                        traceback: str = None) -> dict:
    """
    Shortcut per loggare errore da inviare al server.
    
    Usage:
        from utils.logger import log_error_for_server
        error_data = log_error_for_server('camera', 'CameraTimeout', 'GoPro not responding')
        # Poi invia error_data al server
    """
    return FridgeLogger.log_error_to_server(module, error_type, message, traceback)