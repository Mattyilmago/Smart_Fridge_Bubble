"""
Database Module - MySQL Connection per Smart Fridge
Gestisce connessione e operazioni con database MySQL su server Aruba
"""

import mysql.connector
from mysql.connector import Error, pooling
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager


class DatabaseConfig:
    """Configurazione connessione database MySQL"""
    
    # Configurazione server Aruba DA MODIFICARE
    HOST = "31.11.38.14"
    PORT = 3306
    DATABASE = "Sql1905550_1"
    USER = "Sql1905550"
    PASSWORD = "2PiselliNeri!InGola?"
    
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


class DatabaseManager:
    """Gestisce operazioni database per Smart Fridge"""
    
    def __init__(self, fridge_token: str, use_pool: bool = True):
        """
        Inizializza DatabaseManager
        
        Args:
            fridge_token: Token univoco del frigo (dalla tabella Fridges)
            use_pool: Se True usa connection pooling (consigliato)
        """
        self.fridge_token = fridge_token
        self.fridge_id = None  # Recuperato dal token
        self.use_pool = use_pool
        self._pool = None
        
        if use_pool:
            self._init_connection_pool()
        
        # Recupera fridge_ID dal token
        self._load_fridge_id()
    
    def _init_connection_pool(self):
        """Inizializza il pool di connessioni"""
        try:
            self._pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name=DatabaseConfig.POOL_NAME,
                pool_size=DatabaseConfig.POOL_SIZE,
                **DatabaseConfig.get_config()
            )
            print(f"[DatabaseManager] Connection pool initialized")
        except Error as e:
            print(f"[DatabaseManager] Error creating connection pool: {e}")
            self._pool = None
    
    def _load_fridge_id(self):
        """Recupera fridge_ID dal token"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT ID FROM Fridges WHERE token = %s"
                cursor.execute(query, (self.fridge_token,))
                result = cursor.fetchone()
                cursor.close()
                
                if result:
                    self.fridge_id = result[0]
                    print(f"[DatabaseManager] Fridge ID {self.fridge_id} loaded from token")
                else:
                    raise ValueError(f"Invalid fridge token: {self.fridge_token}")
        except Error as e:
            raise ConnectionError(f"Failed to load fridge ID from token: {e}")
    
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
            print(f"[DatabaseManager] Database error: {e}")
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
                print("[DatabaseManager] Connection test successful")
                return True
        except Error as e:
            print(f"[DatabaseManager] Connection test failed: {e}")
            return False
    
    # ========================================
    # MEASUREMENTS (temperature + power insieme)
    # ========================================
    
    def insert_measurement(self, temperature: float, power: float, 
                          timestamp: Optional[datetime] = None) -> Optional[int]:
        """
        Inserisce misurazione (temperatura + potenza) nel database
        
        Args:
            temperature: Temperatura in °C
            power: Potenza in Watt
            timestamp: Timestamp lettura (default: NOW())
        
        Returns:
            int: ID della misurazione inserita, None se errore
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if timestamp is None:
                    query = """
                        INSERT INTO Measurements (fridge_ID, timestamp, temperature, power)
                        VALUES (%s, NOW(), %s, %s)
                    """
                    cursor.execute(query, (self.fridge_id, temperature, power))
                else:
                    query = """
                        INSERT INTO Measurements (fridge_ID, timestamp, temperature, power)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(query, (self.fridge_id, timestamp, temperature, power))
                
                measurement_id = cursor.lastrowid
                conn.commit()
                cursor.close()
                return measurement_id
        except Error as e:
            # Gestisci errori trigger validazione
            if e.sqlstate == '45000':
                print(f"[DatabaseManager] Validation error: {e.msg}")
                # Temperatura/potenza fuori range - errore sensore
                return None
            else:
                print(f"[DatabaseManager] Database error: {e}")
                return None
    
    def get_measurements_history(self, hours: int = 48) -> List[Dict]:
        """
        Recupera storico misurazioni
        
        Args:
            hours: Numero di ore di storico da recuperare
        
        Returns:
            List[Dict]: Lista di misurazioni con 'timestamp', 'temperature', 'power'
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT timestamp, temperature, power
                    FROM Measurements
                    WHERE fridge_ID = %s
                      AND timestamp >= NOW() - INTERVAL %s HOUR
                    ORDER BY timestamp ASC
                """
                cursor.execute(query, (self.fridge_id, hours))
                results = cursor.fetchall()
                cursor.close()
                return results
        except Error as e:
            print(f"[DatabaseManager] Error fetching measurements: {e}")
            return []
    
    def get_temperature_statistics(self, hours: int = 48) -> Dict:
        """
        Calcola statistiche temperatura per periodo
        
        Args:
            hours: Numero di ore di storico
        
        Returns:
            Dict: Statistiche (count, average, min, max)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT 
                        COUNT(*) as count,
                        AVG(temperature) as average,
                        MIN(temperature) as min_value,
                        MAX(temperature) as max_value
                    FROM Measurements
                    WHERE fridge_ID = %s
                      AND timestamp >= NOW() - INTERVAL %s HOUR
                """
                cursor.execute(query, (self.fridge_id, hours))
                row = cursor.fetchone()
                cursor.close()
                
                if row:
                    return {
                        'count': row[0] or 0,
                        'average': float(row[1]) if row[1] else 0.0,
                        'min': float(row[2]) if row[2] else 0.0,
                        'max': float(row[3]) if row[3] else 0.0
                    }
                return {'count': 0, 'average': 0.0, 'min': 0.0, 'max': 0.0}
        except Error as e:
            print(f"[DatabaseManager] Error getting temperature stats: {e}")
            return {'count': 0, 'average': 0.0, 'min': 0.0, 'max': 0.0}
    
    def get_power_statistics(self, hours: int = 48) -> Dict:
        """
        Calcola statistiche consumo per periodo
        
        Args:
            hours: Numero di ore di storico
        
        Returns:
            Dict: Statistiche (count, average, min, max)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT 
                        COUNT(*) as count,
                        AVG(power) as average,
                        MIN(power) as min_value,
                        MAX(power) as max_value
                    FROM Measurements
                    WHERE fridge_ID = %s
                      AND timestamp >= NOW() - INTERVAL %s HOUR
                """
                cursor.execute(query, (self.fridge_id, hours))
                row = cursor.fetchone()
                cursor.close()
                
                if row:
                    return {
                        'count': row[0] or 0,
                        'average': float(row[1]) if row[1] else 0.0,
                        'min': float(row[2]) if row[2] else 0.0,
                        'max': float(row[3]) if row[3] else 0.0
                    }
                return {'count': 0, 'average': 0.0, 'min': 0.0, 'max': 0.0}
        except Error as e:
            print(f"[DatabaseManager] Error getting power stats: {e}")
            return {'count': 0, 'average': 0.0, 'min': 0.0, 'max': 0.0}
    
    # ========================================
    # ALERTS
    # ========================================
    
    def insert_alert(self, category: str, message: str, 
                    timestamp: Optional[datetime] = None) -> Optional[int]:
        """
        Inserisce allarme nel database
        
        Args:
            category: Categoria allarme (high_temp, door_open, critic_power, ecc.)
            message: Messaggio descrittivo
            timestamp: Timestamp allarme (default: NOW())
        
        Returns:
            int: ID dell'allarme inserito, None se errore
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if timestamp is None:
                    query = """
                        INSERT INTO Alerts (fridge_ID, timestamp, category, message)
                        VALUES (%s, NOW(), %s, %s)
                    """
                    cursor.execute(query, (self.fridge_id, category, message))
                else:
                    query = """
                        INSERT INTO Alerts (fridge_ID, timestamp, category, message)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(query, (self.fridge_id, timestamp, category, message))
                
                alert_id = cursor.lastrowid
                conn.commit()
                cursor.close()
                return alert_id
        except Error as e:
            print(f"[DatabaseManager] Error inserting alert: {e}")
            return None
    
    def get_recent_alerts(self, hours: int = 24, category: Optional[str] = None) -> List[Dict]:
        """
        Recupera allarmi recenti
        
        Args:
            hours: Numero di ore di storico
            category: Filtra per categoria (opzionale)
        
        Returns:
            List[Dict]: Lista allarmi
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                if category:
                    query = """
                        SELECT ID, timestamp, category, message
                        FROM Alerts
                        WHERE fridge_ID = %s
                          AND category = %s
                          AND timestamp >= NOW() - INTERVAL %s HOUR
                        ORDER BY timestamp DESC
                    """
                    cursor.execute(query, (self.fridge_id, category, hours))
                else:
                    query = """
                        SELECT ID, timestamp, category, message
                        FROM Alerts
                        WHERE fridge_ID = %s
                          AND timestamp >= NOW() - INTERVAL %s HOUR
                        ORDER BY timestamp DESC
                    """
                    cursor.execute(query, (self.fridge_id, hours))
                
                results = cursor.fetchall()
                cursor.close()
                return results
        except Error as e:
            print(f"[DatabaseManager] Error fetching alerts: {e}")
            return []
    
    def get_critical_alerts(self, hours: int = 2) -> List[Dict]:
        """
        Recupera alert critici (critic_temp, critic_power, door_left_open, sensor_offline)
        ancora attivi
        
        Args:
            hours: Numero di ore di storico (default: 2)
        
        Returns:
            List[Dict]: Alert critici
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT ID, timestamp, category, message
                    FROM Alerts
                    WHERE fridge_ID = %s
                      AND category IN ('critic_temp', 'critic_power', 'door_left_open', 'sensor_offline')
                      AND timestamp >= NOW() - INTERVAL %s HOUR
                    ORDER BY timestamp DESC
                """
                cursor.execute(query, (self.fridge_id, hours))
                results = cursor.fetchall()
                cursor.close()
                return results
        except Error as e:
            print(f"[DatabaseManager] Error fetching critical alerts: {e}")
            return []
    
    def insert_door_event(self, is_open: bool) -> Optional[int]:
        """
        Inserisce evento porta (aperta/chiusa)
        
        Args:
            is_open: True = porta aperta, False = porta chiusa
        
        Returns:
            int: ID alert inserito
        """
        category = 'door_open' if is_open else 'door_closed'
        message = 'Porta aperta' if is_open else 'Porta chiusa'
        return self.insert_alert(category, message)
    
    # ========================================
    # PRODUCTS & MOVEMENTS
    # ========================================
    
    def add_product_movement(self, product_id: int, quantity: int,
                            timestamp: Optional[datetime] = None) -> Optional[int]:
        """
        Registra movimento prodotto (aggiunta/rimozione)
        Trigger automatico aggiorna ProductsFridge
        
        Args:
            product_id: ID del prodotto
            quantity: Quantità (positivo=aggiunta, negativo=rimozione)
            timestamp: Timestamp movimento (default: NOW())
        
        Returns:
            int: ID movimento, None se errore
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if timestamp is None:
                    query = """
                        INSERT INTO ProductsMovements (fridge_ID, product_ID, quantity, timestamp)
                        VALUES (%s, %s, %s, NOW())
                    """
                    cursor.execute(query, (self.fridge_id, product_id, quantity))
                else:
                    query = """
                        INSERT INTO ProductsMovements (fridge_ID, product_ID, quantity, timestamp)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(query, (self.fridge_id, product_id, quantity, timestamp))
                
                movement_id = cursor.lastrowid
                conn.commit()
                cursor.close()
                return movement_id
        except Error as e:
            # Gestisci errore trigger quantità insufficiente
            if e.sqlstate == '45000':
                print(f"[DatabaseManager] Movement validation error: {e.msg}")
                # Probabilmente quantità insufficiente
                return None
            else:
                print(f"[DatabaseManager] Database error: {e}")
                return None
    
    def get_current_products(self) -> List[Dict]:
        """
        Recupera prodotti attualmente nel frigo (removed_in IS NULL)
        
        Returns:
            List[Dict]: Lista prodotti con nome, brand, quantità
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT 
                        pf.ID as fridge_product_id,
                        p.ID as product_id,
                        p.name,
                        p.brand,
                        p.category,
                        pf.quantity,
                        pf.added_in
                    FROM ProductsFridge pf
                    JOIN Products p ON pf.product_ID = p.ID
                    WHERE pf.fridge_ID = %s
                      AND pf.removed_in IS NULL
                    ORDER BY pf.added_in DESC
                """
                cursor.execute(query, (self.fridge_id,))
                results = cursor.fetchall()
                cursor.close()
                return results
        except Error as e:
            print(f"[DatabaseManager] Error fetching products: {e}")
            return []
    
    def get_product_movements_history(self, hours: int = 168) -> List[Dict]:
        """
        Recupera storico movimenti prodotti (ultima settimana default)
        
        Args:
            hours: Numero di ore di storico (default: 168 = 7 giorni)
        
        Returns:
            List[Dict]: Lista movimenti con dettagli prodotto
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT 
                        pm.ID,
                        pm.timestamp,
                        pm.quantity,
                        p.name,
                        p.brand,
                        p.category
                    FROM ProductsMovements pm
                    JOIN Products p ON pm.product_ID = p.ID
                    WHERE pm.fridge_ID = %s
                      AND pm.timestamp >= NOW() - INTERVAL %s HOUR
                    ORDER BY pm.timestamp DESC
                """
                cursor.execute(query, (self.fridge_id, hours))
                results = cursor.fetchall()
                cursor.close()
                return results
        except Error as e:
            print(f"[DatabaseManager] Error fetching movements: {e}")
            return []
    
    def get_product_by_name(self, name: str) -> Optional[Dict]:
        """
        Cerca prodotto per nome (per YOLO detection)
        
        Args:
            name: Nome prodotto
        
        Returns:
            Dict: Dati prodotto o None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT ID, name, brand, category
                    FROM Products
                    WHERE name LIKE %s
                    LIMIT 1
                """
                cursor.execute(query, (f"%{name}%",))
                result = cursor.fetchone()
                cursor.close()
                return result
        except Error as e:
            print(f"[DatabaseManager] Error finding product: {e}")
            return None


# ========================================
# Funzioni di utilità
# ========================================

def load_fridge_token(token_file: str = "fridge_token.json") -> str:
    """
    Carica token frigo da file JSON
    
    Args:
        token_file: Path al file contenente il token
    
    Returns:
        str: Token del frigo
    """
    import json
    import os
    
    try:
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                data = json.load(f)
                return data.get('token', '')
        else:
            raise FileNotFoundError(f"Token file not found: {token_file}")
    except Exception as e:
        raise ValueError(f"Failed to load token from {token_file}: {e}")

def create_database_manager(fridge_token: str) -> DatabaseManager:
    """
    Factory function per creare DatabaseManager
    
    Args:
        fridge_token: Token univoco del frigo
    
    Returns:
        DatabaseManager: Istanza configurata
    """
    return DatabaseManager(fridge_token=fridge_token, use_pool=True)

def create_database_manager_from_file(token_file: str = "fridge_token.json") -> DatabaseManager:
    """
    Factory function per creare DatabaseManager da file token
    
    Args:
        token_file: Path al file contenente il token
    
    Returns:
        DatabaseManager: Istanza configurata
    """
    token = load_fridge_token(token_file)
    return create_database_manager(token)


if __name__ == "__main__":
    # Test connessione database
    print("=" * 60)
    print("Testing Database Connection...")
    print("=" * 60)
    
    # Test con token hardcoded (usare create_database_manager_from_file !!!!)
    TEST_TOKEN = "ma che bel token"  # Token di test dalla tabella Fridges
    db = create_database_manager(fridge_token=TEST_TOKEN)
    
    if db.test_connection():
        print("\n✓ Database connection successful!")
        
        # Test inserimento misurazione
        measurement_id = db.insert_measurement(temperature=4.5, power=120.5)
        if measurement_id:
            print(f"✓ Measurement insert successful! (ID: {measurement_id})")
        
        # Test recupero storico
        history = db.get_measurements_history(hours=48)
        print(f"✓ Retrieved {len(history)} measurements")
        
        # Test statistiche temperatura
        temp_stats = db.get_temperature_statistics(hours=24)
        print(f"✓ Temperature stats: avg={temp_stats['average']:.2f}°C, min={temp_stats['min']:.2f}, max={temp_stats['max']:.2f}")
        
        # Test statistiche power
        power_stats = db.get_power_statistics(hours=24)
        print(f"✓ Power stats: avg={power_stats['average']:.2f}W, min={power_stats['min']:.2f}, max={power_stats['max']:.2f}")
        
        # Test alert
        alert_id = db.insert_alert('high_temp', 'Temperature too high: 9.5°C')
        if alert_id:
            print(f"✓ Alert insert successful! (ID: {alert_id})")
        
        # Test critical alerts
        critical = db.get_critical_alerts()
        print(f"✓ Retrieved {len(critical)} critical alerts")
        
        # Test door event
        door_alert = db.insert_door_event(is_open=True)
        if door_alert:
            print(f"✓ Door event successful! (ID: {door_alert})")
        
        # Test products
        products = db.get_current_products()
        print(f"✓ Retrieved {len(products)} products in fridge")
        
        # Test product movement (se ci sono prodotti)
        if products:
            test_product_id = products[0]['product_id']
            movement_id = db.add_product_movement(test_product_id, quantity=2)
            if movement_id:
                print(f"✓ Product movement successful! (ID: {movement_id})")
    else:
        print("\n✗ Database connection failed!")
        print("Please enable remote access in Aruba panel or test from Aruba server")
