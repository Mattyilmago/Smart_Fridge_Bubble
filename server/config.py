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
    USER_TOKEN_EXPIRY_DAYS = int(os.getenv('USER_TOKEN_EXPIRY_DAYS', 30))
    RENEWAL_THRESHOLD_DAYS = int(os.getenv('RENEWAL_THRESHOLD_DAYS', 7))
    
    # Converti in timedelta per uso interno
    FRIDGE_TOKEN_EXPIRY = timedelta(days=FRIDGE_TOKEN_EXPIRY_DAYS)
    USER_TOKEN_EXPIRY = timedelta(days=USER_TOKEN_EXPIRY_DAYS)
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
    
    # User Authentication & Validation
    MIN_PASSWORD_LENGTH = int(os.getenv('MIN_PASSWORD_LENGTH', 6))
    MAX_PASSWORD_LENGTH = int(os.getenv('MAX_PASSWORD_LENGTH', 128))
    MIN_EMAIL_LENGTH = int(os.getenv('MIN_EMAIL_LENGTH', 5))
    REQUIRE_PASSWORD_UPPERCASE = os.getenv('REQUIRE_PASSWORD_UPPERCASE', 'False').lower() == 'true'
    REQUIRE_PASSWORD_NUMBERS = os.getenv('REQUIRE_PASSWORD_NUMBERS', 'False').lower() == 'true'
    REQUIRE_PASSWORD_SYMBOLS = os.getenv('REQUIRE_PASSWORD_SYMBOLS', 'False').lower() == 'true'


class APIDefaults:
    """Valori default per parametri API"""
    
    # Measurements
    MEASUREMENTS_HISTORY_HOURS = int(os.getenv('MEASUREMENTS_HISTORY_HOURS', 48))
    TEMPERATURE_STATS_HOURS = int(os.getenv('TEMPERATURE_STATS_HOURS', 48))
    POWER_STATS_HOURS = int(os.getenv('POWER_STATS_HOURS', 48))
    
    # Alerts
    RECENT_ALERTS_HOURS = int(os.getenv('RECENT_ALERTS_HOURS', 24))
    CRITICAL_ALERTS_HOURS = int(os.getenv('CRITICAL_ALERTS_HOURS', 2))
    ALERT_STATISTICS_DAYS = int(os.getenv('ALERT_STATISTICS_DAYS', 7))
    
    # Products
    PRODUCT_MOVEMENTS_HOURS = int(os.getenv('PRODUCT_MOVEMENTS_HOURS', 168))  # 7 giorni
    SHOPPING_LIST_HOURS = int(os.getenv('SHOPPING_LIST_HOURS', 48))
    MOST_CONSUMED_DAYS = int(os.getenv('MOST_CONSUMED_DAYS', 30))
    MOST_CONSUMED_LIMIT = int(os.getenv('MOST_CONSUMED_LIMIT', 10))
    
    # Energy & Analytics
    ENERGY_CONSUMPTION_HOURS = int(os.getenv('ENERGY_CONSUMPTION_HOURS', 24))
    ENERGY_COST_PER_KWH = float(os.getenv('ENERGY_COST_PER_KWH', 0.25))  # Euro per kWh
    HOURLY_PATTERN_HOURS = int(os.getenv('HOURLY_PATTERN_HOURS', 168))  # 7 giorni
    TEMPERATURE_TREND_HOURS = int(os.getenv('TEMPERATURE_TREND_HOURS', 6))
    DOOR_STATISTICS_HOURS = int(os.getenv('DOOR_STATISTICS_HOURS', 24))


class SensorThresholds:
    """Soglie sensori e validazione"""
    
    # Temperature (°C)
    TEMP_MIN_VALID = float(os.getenv('TEMP_MIN_VALID', -40.0))
    TEMP_MAX_VALID = float(os.getenv('TEMP_MAX_VALID', 60.0))
    TEMP_LOW_THRESHOLD = float(os.getenv('TEMP_LOW_THRESHOLD', 12.0))  # Zona congelamento
    TEMP_HIGH_WARNING = float(os.getenv('TEMP_HIGH_WARNING', 20.0))  # Zona gialla
    TEMP_HIGH_CRITICAL = float(os.getenv('TEMP_HIGH_CRITICAL', 25.0))  # Zona rossa
    TEMP_TREND_THRESHOLD = float(os.getenv('TEMP_TREND_THRESHOLD', 0.5))  # °C per trend significativo
    
    # Power (Watt)
    POWER_MIN_VALID = float(os.getenv('POWER_MIN_VALID', 0.0))
    POWER_MAX_VALID = float(os.getenv('POWER_MAX_VALID', 10000.0))
    POWER_CRITICAL_THRESHOLD = float(os.getenv('POWER_CRITICAL_THRESHOLD', 500.0))  # Watt
    
    # Door
    DOOR_LEFT_OPEN_SECONDS = int(os.getenv('DOOR_LEFT_OPEN_SECONDS', 120))  # 2 minuti


class DatabaseConfig:
    """Configurazione database MySQL (per compatibilità con db_manager.py)"""
    
    HOST = Config.DB_HOST
    PORT = Config.DB_PORT
    DATABASE = Config.DB_NAME
    USER = Config.DB_USER
    PASSWORD = Config.DB_PASSWORD
    
    POOL_NAME = os.getenv('DB_POOL_NAME', "smart_fridge_pool")
    POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 5))
    CONNECTION_TIMEOUT = int(os.getenv('DB_CONNECTION_TIMEOUT', 10))
    CHARSET = os.getenv('DB_CHARSET', 'utf8mb4')
    AUTOCOMMIT = os.getenv('DB_AUTOCOMMIT', 'False').lower() == 'true'
    RAISE_ON_WARNINGS = os.getenv('DB_RAISE_ON_WARNINGS', 'True').lower() == 'true'
    
    @classmethod
    def get_config(cls) -> dict:
        """Ritorna dizionario configurazione per mysql.connector"""
        return {
            'host': cls.HOST,
            'port': cls.PORT,
            'database': cls.DATABASE,
            'user': cls.USER,
            'password': cls.PASSWORD,
            'charset': cls.CHARSET,
            'use_unicode': True,                
            'autocommit': cls.AUTOCOMMIT,
            'raise_on_warnings': cls.RAISE_ON_WARNINGS,
            'connection_timeout': cls.CONNECTION_TIMEOUT
        }