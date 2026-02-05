"""
Query SQL per autenticazione
Funzioni helper per le route auth
"""

import mysql.connector
from mysql.connector import Error
from typing import Optional
from contextlib import contextmanager
from config import DatabaseConfig
from utils.logger import get_logger

logger = get_logger('database')


class AuthQueries:
    """Query database per autenticazione fridges"""
    
    def __init__(self, use_pool: bool = True):
        """
        Inizializza gestore query
        
        Args:
            use_pool: Se True usa connection pooling
        """
        self.use_pool = use_pool
        self._pool = None
        
        if use_pool:
            self._init_connection_pool()
    
    def _init_connection_pool(self):
        """Inizializza pool connessioni"""
        try:
            self._pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name=DatabaseConfig.POOL_NAME,
                pool_size=DatabaseConfig.POOL_SIZE,
                **DatabaseConfig.get_config()
            )
            logger.info("Connection pool initialized")
        except Error as e:
            logger.error(f"Error creating connection pool: {e}")
            self._pool = None
    
    @contextmanager
    def get_connection(self):
        """Context manager per connessione database"""
        connection = None
        try:
            if self.use_pool and self._pool:
                connection = self._pool.get_connection()
            else:
                connection = mysql.connector.connect(**DatabaseConfig.get_config())
            
            yield connection
            
        except Error as e:
            logger.error(f"Database error: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
    
    def user_exists(self, user_id: int) -> bool:
        """
        Verifica se utente esiste
        
        Args:
            user_id: ID utente
        
        Returns:
            bool: True se esiste
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT ID FROM Users WHERE ID = %s"
                cursor.execute(query, (user_id,))
                result = cursor.fetchone()
                cursor.close()
                return result is not None
        except Error as e:
            logger.error(f"Error checking user existence: {e}")
            return False
    
    def create_fridge(self, user_id: int, position: str) -> Optional[int]:
        """
        Crea nuovo frigo nel database
        
        Args:
            user_id: ID utente proprietario
            position: Posizione frigo (es. "Cucina")
        
        Returns:
            int: fridge_id del frigo creato, None se errore
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    INSERT INTO Fridges (user_ID, position)
                    VALUES (%s, %s)
                """
                cursor.execute(query, (user_id, position))
                fridge_id = cursor.lastrowid
                conn.commit()
                cursor.close()
                
                logger.info(f"Frigo {fridge_id} creato per user {user_id}, posizione: {position}")
                return fridge_id
        except Error as e:
            logger.error(f"Error creating fridge: {e}")
            return None
    
    def get_fridge_owner(self, fridge_id: int) -> Optional[int]:
        """
        Recupera user_ID proprietario del frigo
        
        Args:
            fridge_id: ID frigo
        
        Returns:
            int: user_ID o None se frigo non esiste
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT user_ID FROM Fridges WHERE ID = %s"
                cursor.execute(query, (fridge_id,))
                result = cursor.fetchone()
                cursor.close()
                
                if result:
                    return result[0]
                return None
        except Error as e:
            logger.error(f"Error getting fridge owner: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Testa connessione database
        
        Returns:
            bool: True se connessione OK
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                logger.info("Connection test successful")
                return True
        except Error as e:
            logger.error(f"Connection test failed: {e}")
            return False