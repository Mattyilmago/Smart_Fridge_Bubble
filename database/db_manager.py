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
    
    def __init__(self, fridge_id: int = 1, use_pool: bool = True):
        """
        Inizializza DatabaseManager
        
        Args:
            fridge_id: ID del frigo (dalla tabella Fridges)
            use_pool: Se True usa connection pooling (consigliato)
        """
        self.fridge_id = fridge_id
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
            print(f"[DatabaseManager] Connection pool initialized")
        except Error as e:
            print(f"[DatabaseManager] Error creating connection pool: {e}")
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
            print(f"[DatabaseManager] Error inserting measurement: {e}")
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
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """
        Recupera allarmi recenti
        
        Args:
            hours: Numero di ore di storico
        
        Returns:
            List[Dict]: Lista allarmi
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
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


# ========================================
# Funzioni di utilità
# ========================================

def create_database_manager(fridge_id: int = 1) -> DatabaseManager:
    """
    Factory function per creare DatabaseManager
    
    Args:
        fridge_id: ID del frigo
    
    Returns:
        DatabaseManager: Istanza configurata
    """
    return DatabaseManager(fridge_id=fridge_id, use_pool=True)


if __name__ == "__main__":
    # Test connessione database
    print("=" * 60)
    print("Testing Database Connection...")
    print("=" * 60)
    
    db = create_database_manager(fridge_id=1)
    
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
    else:
        print("\n✗ Database connection failed!")
        print("Please enable remote access in Aruba panel or test from Aruba server")
