"""
Logger centralizzato per Smart Fridge Server
Formato identico al logger del Raspberry
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config import Config


class ServerLogger:
    """Logger centralizzato con rotazione file"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, module_name: str) -> logging.Logger:
        """
        Ottiene o crea logger per modulo
        
        Args:
            module_name: Nome modulo (es. "auth", "database")
        
        Returns:
            logging.Logger configurato
        """
        if module_name in cls._loggers:
            return cls._loggers[module_name]
        
        logger = logging.getLogger(f"SmartFridge.{module_name}")
        logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        if logger.handlers:
            cls._loggers[module_name] = logger
            return logger
        
        # Crea directory logs se non esiste
        log_dir = Path(Config.LOG_FILE).parent
        log_dir.mkdir(exist_ok=True)
        
        # File handler con rotazione
        file_handler = RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=Config.LOG_MAX_SIZE_MB * 1024 * 1024,
            backupCount=Config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        
        # Formato: [timestamp] [modulo] [livello] messaggio
        formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        cls._loggers[module_name] = logger
        return logger


def get_logger(module_name: str) -> logging.Logger:
    """
    Shortcut per ottenere logger
    
    Usage:
        from utils.logger import get_logger
        logger = get_logger('auth')
        logger.info("Frigo registrato")
    """
    return ServerLogger.get_logger(module_name)