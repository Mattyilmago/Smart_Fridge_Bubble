"""
Debug Database Operations
Gestisce operazioni database per debug e amministrazione
"""

from typing import List, Dict, Optional, Any
from mysql.connector import Error
from datetime import datetime
from .connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger('database.debug')


class DebugDatabase(DatabaseConnection):
    """
    Gestisce operazioni database per debug e amministrazione
    """
    
    # Tabelle accessibili tramite API di debug
    ALLOWED_TABLES = [
        'Users',
        'Fridges',
        'Measurements',
        'Alerts',
        'Products',
        'Product_Movements'
    ]
    
    def __init__(self, use_pool: bool = True):
        """
        Inizializza DebugDatabase
        
        Args:
            use_pool: Se True usa connection pooling (consigliato)
        """
        super().__init__(use_pool)
        logger.info("DebugDatabase initialized")
    
    def get_all_tables(self) -> Optional[List[str]]:
        """
        Ottiene lista di tutte le tabelle accessibili
        
        Returns:
            List[str]: Lista nomi tabelle, None se errore
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE()
                    AND table_name IN ({})
                    ORDER BY table_name
                """.format(','.join(['%s'] * len(self.ALLOWED_TABLES)))
                
                cursor.execute(query, self.ALLOWED_TABLES)
                tables = [row[0] for row in cursor.fetchall()]
                
                logger.info(f"Retrieved {len(tables)} tables")
                return tables
                
        except Error as e:
            logger.error(f"Error getting tables list: {e}")
            return None
    
    def get_table_count(self, table_name: str) -> Optional[int]:
        """
        Conta numero righe in una tabella
        
        Args:
            table_name: Nome della tabella
            
        Returns:
            int: Numero di righe, None se errore
        """
        # Validazione nome tabella
        if table_name not in self.ALLOWED_TABLES:
            logger.warning(f"Tentativo accesso a tabella non consentita: {table_name}")
            return None
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Usa query parametrizzata sicura
                query = f"SELECT COUNT(*) FROM {table_name}"
                cursor.execute(query)
                
                count = cursor.fetchone()[0]
                logger.info(f"Table {table_name} has {count} rows")
                return count
                
        except Error as e:
            logger.error(f"Error counting rows in {table_name}: {e}")
            return None
    
    def get_table_data(self, table_name: str, limit: int = 100, 
                       offset: int = 0) -> Optional[List[Dict[str, Any]]]:
        """
        Recupera dati da una tabella con paginazione (SELECT *)
        
        Args:
            table_name: Nome della tabella
            limit: Numero massimo di righe da recuperare (max 1000)
            offset: Numero di righe da saltare
            
        Returns:
            List[Dict]: Lista di dizionari con i dati, None se errore
        """
        # Validazione nome tabella
        if table_name not in self.ALLOWED_TABLES:
            logger.warning(f"Tentativo accesso a tabella non consentita: {table_name}")
            return None
        
        # Validazione e limiti di sicurezza
        limit = min(max(1, limit), 1000)  # Tra 1 e 1000
        offset = max(0, offset)  # Non negativo
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                # Query sicura con nome tabella validato
                query = f"SELECT * FROM {table_name} LIMIT %s OFFSET %s"
                cursor.execute(query, (limit, offset))
                
                rows = cursor.fetchall()
                
                # Converti datetime in stringhe per JSON serialization
                for row in rows:
                    for key, value in row.items():
                        if isinstance(value, datetime):
                            row[key] = value.isoformat()
                
                logger.info(f"Retrieved {len(rows)} rows from {table_name} "
                           f"(limit={limit}, offset={offset})")
                return rows
                
        except Error as e:
            logger.error(f"Error retrieving data from {table_name}: {e}")
            return None
    
    def get_table_schema(self, table_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Ottiene schema (colonne) di una tabella
        
        Args:
            table_name: Nome della tabella
            
        Returns:
            List[Dict]: Lista informazioni colonne, None se errore
        """
        # Validazione nome tabella
        if table_name not in self.ALLOWED_TABLES:
            logger.warning(f"Tentativo accesso a tabella non consentita: {table_name}")
            return None
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                query = """
                    SELECT 
                        COLUMN_NAME as name,
                        DATA_TYPE as type,
                        IS_NULLABLE as nullable,
                        COLUMN_KEY as key_type,
                        COLUMN_DEFAULT as default_value,
                        EXTRA as extra
                    FROM information_schema.COLUMNS
                    WHERE table_schema = DATABASE()
                    AND table_name = %s
                    ORDER BY ORDINAL_POSITION
                """
                
                cursor.execute(query, (table_name,))
                schema = cursor.fetchall()
                
                logger.info(f"Retrieved schema for {table_name} ({len(schema)} columns)")
                return schema
                
        except Error as e:
            logger.error(f"Error getting schema for {table_name}: {e}")
            return None



    def insert_products_batch(self, products: List[str], categories: Optional[List[str]] = None) -> Optional[List[int]]:
        """
        Inserisce multipli prodotti in batch
        
        Args:
            products: Lista prodotti da inserire
            categories: Lista categorie (opzionale, stessa lunghezza)
        
        Returns:
            List[int]: Lista ID prodotti inseriti, None se errore
        """
        if len(products) != len(categories) and categories is not None:
            print(f"[FridgeDatabase] Products and categories length mismatch")
            return None
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                product_ids = []
                
                # Prepara batch insert
                if categories is None:
                    query = """
                        INSERT INTO Products (name, category)
                        VALUES (%s, %s)
                    """
                    values = [(p,) for p in products]
                else:
                    query = """
                        INSERT INTO Products (name, category)
                        VALUES (%s, %s)
                    """
                    values = [(p, c) for p, c in zip(products, categories)]
                
                # Esegui batch insert
                cursor.executemany(query, values)
                
                # Recupera gli ID inseriti (lastrowid per batch è l'ID del primo record)
                first_id = cursor.lastrowid
                count = cursor.rowcount
                product_ids = list(range(first_id, first_id + count))
                
                conn.commit()
                cursor.close()
                
                print(f"[FridgeDatabase] Batch inserted {count} products with IDs: {product_ids}")
                return product_ids
                
        except Error as e:
            # Gestisci errori trigger validazione
            if e.sqlstate == '45000':
                print(f"[FridgeDatabase] Validation error in batch: {e.msg}")
                return None
            else:
                print(f"[FridgeDatabase] Database error in batch: {e}")
                return None