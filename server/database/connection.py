"""
Database Connection Manager
Gestisce connessioni e pool per MySQL
"""

import mysql.connector
from mysql.connector import Error, pooling
from contextlib import contextmanager
from config import Config


class DatabaseConfig:
    """Configurazione connessione database MySQL"""
    
    # Legge configurazione da .env tramite Config
    HOST = Config.DB_HOST
    PORT = Config.DB_PORT
    DATABASE = Config.DB_NAME
    USER = Config.DB_USER
    PASSWORD = Config.DB_PASSWORD
    
    # Pool connessioni
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


class DatabaseConnection:
    """Classe base per gestione connessioni database"""
    
    def __init__(self, use_pool: bool = True):
        """
        Inizializza connessione database
        
        Args:
            use_pool: Se True usa connection pooling (consigliato)
        """
        self.use_pool = use_pool
        self._pool = None
        
        if use_pool:
            self._init_connection_pool()
    
    def _init_connection_pool(self):
        """Inizializza il pool di connessioni"""
        try:
            self._pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name=DatabaseConfig.POOL_NAME,
                pool_size=DatabaseConfig.POOL_SIZE,
                **DatabaseConfig.get_config()
            )
            print(f"[DatabaseConnection] Connection pool initialized")
        except Error as e:
            print(f"[DatabaseConnection] Error creating connection pool: {e}")
            self._pool = None
    
    @contextmanager
    def get_connection(self):
        """
        Context manager per ottenere connessione database.
        Gestisce automaticamente apertura/chiusura.
        
        Yields:
            mysql.connector.connection: Connessione attiva
        """
        connection = None
        try:
            if self.use_pool and self._pool:
                connection = self._pool.get_connection()
            else:
                connection = mysql.connector.connect(**DatabaseConfig.get_config())
            
            yield connection
            
        except Error as e:
            print(f"[DatabaseConnection] Database error: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
    
    def test_connection(self) -> bool:
        """
        Testa la connessione al database
        
        Returns:
            bool: True se connessione ok, False altrimenti
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                print("[DatabaseConnection] Connection test successful")
                return True
        except Error as e:
            print(f"[DatabaseConnection] Connection test failed: {e}")
            return False
