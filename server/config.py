"""
Configurazione centralizzata per Smart Fridge Server
Carica variabili da .env e le rende disponibili come costanti
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Carica variabili da .env
load_dotenv()


class Config:
    """Configurazione generale applicazione"""
    
    # Flask
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY or JWT_SECRET_KEY == 'CHANGE-THIS-TO-A-RANDOM-SECRET-KEY-MIN-32-CHARS-PLEASE':
        raise ValueError("JWT_SECRET_KEY must be set in .env file!")
    
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    FRIDGE_TOKEN_EXPIRY_DAYS = int(os.getenv('FRIDGE_TOKEN_EXPIRY_DAYS', 30))
    RENEWAL_THRESHOLD_DAYS = int(os.getenv('RENEWAL_THRESHOLD_DAYS', 7))
    
    # Converti in timedelta per uso interno
    FRIDGE_TOKEN_EXPIRY = timedelta(days=FRIDGE_TOKEN_EXPIRY_DAYS)
    RENEWAL_THRESHOLD = timedelta(days=RENEWAL_THRESHOLD_DAYS)
    
    # Database
    DB_HOST = os.getenv('DB_HOST', '31.11.38.14')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_NAME = os.getenv('DB_NAME', 'Sql1905550_1')
    DB_USER = os.getenv('DB_USER', 'Sql1905550')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    
    if not DB_PASSWORD:
        raise ValueError("DB_PASSWORD must be set in .env file!")
    
    # Rate Limiting
    RATE_LIMIT_REGISTER_PER_HOUR = int(os.getenv('RATE_LIMIT_REGISTER_PER_HOUR', 10))
    RATE_LIMIT_RENEW_PER_HOUR = int(os.getenv('RATE_LIMIT_RENEW_PER_HOUR', 20))
    RATE_LIMIT_IS_AUTHORIZED_PER_DAY = int(os.getenv('RATE_LIMIT_IS_AUTHORIZED_PER_DAY', 200))
    
    # Logging
    LOG_FILE = os.getenv('LOG_FILE', 'logs/server.log')
    LOG_MAX_SIZE_MB = int(os.getenv('LOG_MAX_SIZE_MB', 10))
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


class DatabaseConfig:
    """Configurazione database MySQL (per compatibilità con db_manager.py)"""
    
    HOST = Config.DB_HOST
    PORT = Config.DB_PORT
    DATABASE = Config.DB_NAME
    USER = Config.DB_USER
    PASSWORD = Config.DB_PASSWORD
    
    POOL_NAME = "smart_fridge_pool"
    POOL_SIZE = 5
    
    @classmethod
    def get_config(cls) -> dict:
        """Ritorna dizionario configurazione per mysql.connector"""
        return {
            'host': cls.HOST,
            'port': cls.PORT,
            'database': cls.DATABASE,
            'user': cls.USER,
            'password': cls.PASSWORD,
            'charset': 'utf8mb4',
            'use_unicode': True,
            'autocommit': False,
            'raise_on_warnings': True,
            'connection_timeout': 10
        }