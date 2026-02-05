"""
Fridge Database Operations
Gestisce operazioni database lato frigo (measurements, alerts, products)
"""

from mysql.connector import Error
from datetime import datetime
from typing import List, Dict, Optional
from .connection import DatabaseConnection


class FridgeDatabase(DatabaseConnection):
    """
    Gestisce operazioni database per Smart Fridge (operazioni lato frigo)
    
    Classe stateless: il fridge_id viene passato come parametro in ogni funzione.
    Questo permette di gestire richieste concorrenti da frigo diversi.
    """
    
    def __init__(self, use_pool: bool = True):
        """
        Inizializza FridgeDatabase
        
        Args:
            use_pool: Se True usa connection pooling (consigliato)
        """
        super().__init__(use_pool)
    
    # ========================================
    # MEASUREMENTS (temperature + power insieme)
    # ========================================
    
    def insert_measurement(self, fridge_id: int, temperature: float, power: float, 
                          timestamp: Optional[datetime] = None) -> Optional[int]:
        """
        Inserisce misurazione (temperatura + potenza) nel database
        
        Args:
            fridge_id: ID del frigo
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
                    cursor.execute(query, (fridge_id, temperature, power))
                else:
                    query = """
                        INSERT INTO Measurements (fridge_ID, timestamp, temperature, power)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(query, (fridge_id, timestamp, temperature, power))
                
                measurement_id = cursor.lastrowid
                conn.commit()
                cursor.close()
                return measurement_id
        except Error as e:
            # Gestisci errori trigger validazione
            if e.sqlstate == '45000':
                print(f"[FridgeDatabase] Validation error: {e.msg}")
                # Temperatura/potenza fuori range - errore sensore
                return None
            else:
                print(f"[FridgeDatabase] Database error: {e}")
                return None
    
    def insert_measurements_batch(self, fridge_id: int, temperatures: List[float], 
                                 powers: List[float], timestamps: Optional[List[datetime]] = None) -> Optional[List[int]]:
        """
        Inserisce multiple misurazioni in batch (più efficiente)
        
        Args:
            fridge_id: ID del frigo
            temperatures: Lista temperature in °C
            powers: Lista potenze in Watt (stessa lunghezza di temperatures)
            timestamps: Lista timestamp (opzionale, stessa lunghezza)
        
        Returns:
            List[int]: Lista ID misurazioni inserite, None se errore
        """
        if len(temperatures) != len(powers):
            print(f"[FridgeDatabase] Temperatures and powers length mismatch")
            return None
        
        if timestamps and len(timestamps) != len(temperatures):
            print(f"[FridgeDatabase] Timestamps length mismatch")
            return None
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                measurement_ids = []
                
                # Prepara batch insert
                if timestamps is None:
                    query = """
                        INSERT INTO Measurements (fridge_ID, timestamp, temperature, power)
                        VALUES (%s, NOW(), %s, %s)
                    """
                    values = [(fridge_id, temp, pwr) for temp, pwr in zip(temperatures, powers)]
                else:
                    query = """
                        INSERT INTO Measurements (fridge_ID, timestamp, temperature, power)
                        VALUES (%s, %s, %s, %s)
                    """
                    values = [(fridge_id, ts, temp, pwr) for ts, temp, pwr in zip(timestamps, temperatures, powers)]
                
                # Esegui batch insert
                cursor.executemany(query, values)
                
                # Recupera gli ID inseriti (lastrowid per batch è l'ID del primo record)
                first_id = cursor.lastrowid
                count = cursor.rowcount
                measurement_ids = list(range(first_id, first_id + count))
                
                conn.commit()
                cursor.close()
                
                print(f"[FridgeDatabase] Batch inserted {count} measurements for fridge {fridge_id}")
                return measurement_ids
                
        except Error as e:
            # Gestisci errori trigger validazione
            if e.sqlstate == '45000':
                print(f"[FridgeDatabase] Validation error in batch: {e.msg}")
                return None
            else:
                print(f"[FridgeDatabase] Database error in batch: {e}")
                return None
    
    def get_measurements_history(self, fridge_id: int, hours: int = 48) -> List[Dict]:
        """
        Recupera storico misurazioni
        
        Args:
            fridge_id: ID del frigo
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
                cursor.execute(query, (fridge_id, hours))
                results = cursor.fetchall()
                cursor.close()
                return results
        except Error as e:
            print(f"[FridgeDatabase] Error fetching measurements: {e}")
            return []
    
    def get_temperature_statistics(self, fridge_id: int, hours: int = 48) -> Dict:
        """
        Calcola statistiche temperatura per periodo
        
        Args:
            fridge_id: ID del frigo
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
                cursor.execute(query, (fridge_id, hours))
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
            print(f"[FridgeDatabase] Error getting temperature stats: {e}")
            return {'count': 0, 'average': 0.0, 'min': 0.0, 'max': 0.0}
    
    def get_power_statistics(self, fridge_id: int, hours: int = 48) -> Dict:
        """
        Calcola statistiche consumo per periodo
        
        Args:
            fridge_id: ID del frigo
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
                cursor.execute(query, (fridge_id, hours))
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
            print(f"[FridgeDatabase] Error getting power stats: {e}")
            return {'count': 0, 'average': 0.0, 'min': 0.0, 'max': 0.0}
    
    # ========================================
    # ALERTS
    # ========================================
    
    def insert_alert(self, fridge_id: int, category: str, message: str, 
                    timestamp: Optional[datetime] = None) -> Optional[int]:
        """
        Inserisce allarme nel database
        
        Args:
            fridge_id: ID del frigo
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
                    cursor.execute(query, (fridge_id, category, message))
                else:
                    query = """
                        INSERT INTO Alerts (fridge_ID, timestamp, category, message)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(query, (fridge_id, timestamp, category, message))
                
                alert_id = cursor.lastrowid
                conn.commit()
                cursor.close()
                return alert_id
        except Error as e:
            print(f"[FridgeDatabase] Error inserting alert: {e}")
            return None
    
    def get_recent_alerts(self, fridge_id: int, hours: int = 24, category: Optional[str] = None) -> List[Dict]:
        """
        Recupera allarmi recenti
        
        Args:
            fridge_id: ID del frigo
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
                    cursor.execute(query, (fridge_id, category, hours))
                else:
                    query = """
                        SELECT ID, timestamp, category, message
                        FROM Alerts
                        WHERE fridge_ID = %s
                          AND timestamp >= NOW() - INTERVAL %s HOUR
                        ORDER BY timestamp DESC
                    """
                    cursor.execute(query, (fridge_id, hours))
                
                results = cursor.fetchall()
                cursor.close()
                return results
        except Error as e:
            print(f"[FridgeDatabase] Error fetching alerts: {e}")
            return []
    
    def get_critical_alerts(self, fridge_id: int, hours: int = 24) -> List[Dict]:
        """
        Recupera alert critici (critic_temp, critic_power, door_left_open, sensor_offline, low_temp)
        ancora attivi
        
        Args:
            fridge_id: ID del frigo
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
                      AND category IN ('critic_temp', 'critic_power', 'door_left_open', 'sensor_offline', 'low_temp')
                      AND timestamp >= NOW() - INTERVAL %s HOUR
                    ORDER BY timestamp DESC
                """
                cursor.execute(query, (fridge_id, hours))
                results = cursor.fetchall()
                cursor.close()
                return results
        except Error as e:
            print(f"[FridgeDatabase] Error fetching critical alerts: {e}")
            return []
    
    def insert_door_event(self, fridge_id: int, is_open: bool) -> Optional[int]:
        """
        Inserisce evento porta (aperta/chiusa)
        
        Args:
            fridge_id: ID del frigo
            is_open: True = porta aperta, False = porta chiusa
        
        Returns:
            int: ID alert inserito
        """
        category = 'door_open' if is_open else 'door_closed'
        message = 'Porta aperta' if is_open else 'Porta chiusa'
        return self.insert_alert(fridge_id, category, message)
    
    # ========================================
    # PRODUCTS & MOVEMENTS
    # ========================================
    
    def add_product_movement(self, fridge_id: int, product_id: int, quantity: int,
                            timestamp: Optional[datetime] = None) -> Optional[int]:
        """
        Registra movimento prodotto (aggiunta/rimozione)
        Trigger automatico aggiorna ProductsFridge
        
        Args:
            fridge_id: ID del frigo
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
                    cursor.execute(query, (fridge_id, product_id, quantity))
                else:
                    query = """
                        INSERT INTO ProductsMovements (fridge_ID, product_ID, quantity, timestamp)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(query, (fridge_id, product_id, quantity, timestamp))
                
                movement_id = cursor.lastrowid
                conn.commit()
                cursor.close()
                return movement_id
        except Error as e:
            # Gestisci errore trigger quantità insufficiente
            if e.sqlstate == '45000':
                print(f"[FridgeDatabase] Movement validation error: {e.msg}")
                # Probabilmente quantità insufficiente
                return None
            else:
                print(f"[FridgeDatabase] Database error: {e}")
                return None
    
    def get_current_products(self, fridge_id: int) -> List[Dict]:
        """
        Recupera prodotti attualmente nel frigo (removed_in IS NULL)
        
        Args:
            fridge_id: ID del frigo
        
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
                cursor.execute(query, (fridge_id,))
                results = cursor.fetchall()
                cursor.close()
                return results
        except Error as e:
            print(f"[FridgeDatabase] Error fetching products: {e}")
            return []
    
    def get_latest_measurement(self, fridge_id: int) -> Optional[Dict]:
        """
        Recupera l'ultima misurazione del frigo
        
        Args:
            fridge_id: ID del frigo
        
        Returns:
            Dict: Ultima misurazione con timestamp, temperature, power
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT timestamp, temperature, power
                    FROM Measurements
                    WHERE fridge_ID = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                """
                cursor.execute(query, (fridge_id,))
                result = cursor.fetchone()
                cursor.close()
                return result
        except Error as e:
            print(f"[FridgeDatabase] Error fetching latest measurement: {e}")
            return None
    
    def get_product_movements_history(self, fridge_id: int, hours: int = 168) -> List[Dict]:
        """
        Recupera storico movimenti prodotti (ultima settimana default)
        
        Args:
            fridge_id: ID del frigo
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
                cursor.execute(query, (fridge_id, hours))
                results = cursor.fetchall()
                cursor.close()
                return results
        except Error as e:
            print(f"[FridgeDatabase] Error fetching movements: {e}")
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
            print(f"[FridgeDatabase] Error finding product: {e}")
            return None
    
    # ========================================
    # ADVANCED ANALYTICS
    # ========================================
    
    def calculate_energy_consumption(self, fridge_id: int, hours: int = 24) -> float:
        """
        Calcola consumo energetico in kWh per periodo
        Formula: somma di (potenza * intervallo_tempo) / 1000
        
        Args:
            fridge_id: ID del frigo
            hours: Numero di ore da considerare
        
        Returns:
            float: kWh consumati nel periodo
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT 
                        power,
                        timestamp,
                        LEAD(timestamp) OVER (ORDER BY timestamp) as next_timestamp
                    FROM Measurements
                    WHERE fridge_ID = %s
                      AND timestamp >= NOW() - INTERVAL %s HOUR
                    ORDER BY timestamp ASC
                """
                cursor.execute(query, (fridge_id, hours))
                rows = cursor.fetchall()
                cursor.close()
                
                if not rows:
                    return 0.0
                
                # Calcola energia sommando potenza * intervallo
                total_kwh = 0.0
                for row in rows:
                    if row[2] is not None:  # next_timestamp esiste
                        power_watts = float(row[0])
                        time_diff_seconds = (row[2] - row[1]).total_seconds()
                        time_diff_hours = time_diff_seconds / 3600.0
                        energy_wh = power_watts * time_diff_hours
                        total_kwh += energy_wh / 1000.0
                
                return round(total_kwh, 3)
        except Error as e:
            print(f"[FridgeDatabase] Error calculating energy consumption: {e}")
            return 0.0
    
    def calculate_energy_cost(self, fridge_id: int, hours: int = 24, cost_per_kwh: float = 0.25) -> float:
        """
        Calcola costo energetico stimato
        
        Args:
            fridge_id: ID del frigo
            hours: Numero di ore
            cost_per_kwh: Costo al kWh in euro (default 0.25€)
        
        Returns:
            float: Costo in euro
        """
        kwh = self.calculate_energy_consumption(fridge_id, hours)
        return round(kwh * cost_per_kwh, 2)
    
    def get_temperature_trend(self, fridge_id: int, hours: int = 6) -> str:
        """
        Determina trend temperatura (crescente/decrescente/stabile)
        Confronta media prime metà vs seconda metà del periodo
        
        Args:
            fridge_id: ID del frigo
            hours: Ore da analizzare
        
        Returns:
            str: 'increasing', 'decreasing', 'stable'
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Media prima metà periodo
                query_first = """
                    SELECT AVG(temperature) as avg_temp
                    FROM Measurements
                    WHERE fridge_ID = %s
                      AND timestamp >= NOW() - INTERVAL %s HOUR
                      AND timestamp < NOW() - INTERVAL %s HOUR
                """
                half_hours = hours / 2
                cursor.execute(query_first, (fridge_id, hours, half_hours))
                first_half = cursor.fetchone()
                
                # Media seconda metà periodo
                query_second = """
                    SELECT AVG(temperature) as avg_temp
                    FROM Measurements
                    WHERE fridge_ID = %s
                      AND timestamp >= NOW() - INTERVAL %s HOUR
                """
                cursor.execute(query_second, (fridge_id, half_hours))
                second_half = cursor.fetchone()
                cursor.close()
                
                if not first_half[0] or not second_half[0]:
                    return 'stable'
                
                first_avg = float(first_half[0])
                second_avg = float(second_half[0])
                diff = second_avg - first_avg
                
                # Soglia configurabile per considerarlo cambio significativo
                from config import SensorThresholds
                threshold = SensorThresholds.TEMP_TREND_THRESHOLD
                if diff > threshold:
                    return 'increasing'
                elif diff < -threshold:
                    return 'decreasing'
                else:
                    return 'stable'
        except Error as e:
            print(f"[FridgeDatabase] Error calculating temperature trend: {e}")
            return 'stable'
    
    def get_door_open_statistics(self, fridge_id: int, hours: int = 24) -> Dict:
        """
        Calcola statistiche aperture porta
        
        Args:
            fridge_id: ID del frigo
            hours: Ore da analizzare
        
        Returns:
            Dict: {
                'total_openings': int,
                'avg_open_seconds': float,
                'max_open_seconds': float,
                'total_open_seconds': float
            }
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Recupera tutti gli eventi porta nel periodo
                query = """
                    SELECT timestamp, category
                    FROM Alerts
                    WHERE fridge_ID = %s
                      AND category IN ('door_open', 'door_closed')
                      AND timestamp >= NOW() - INTERVAL %s HOUR
                    ORDER BY timestamp ASC
                """
                cursor.execute(query, (fridge_id, hours))
                events = cursor.fetchall()
                cursor.close()
                
                if not events:
                    return {
                        'total_openings': 0,
                        'avg_open_seconds': 0.0,
                        'max_open_seconds': 0.0,
                        'total_open_seconds': 0.0
                    }
                
                # Calcola durate aperture
                openings = []
                open_time = None
                
                for timestamp, category in events:
                    if category == 'door_open':
                        open_time = timestamp
                    elif category == 'door_closed' and open_time:
                        duration = (timestamp - open_time).total_seconds()
                        openings.append(duration)
                        open_time = None
                
                if not openings:
                    return {
                        'total_openings': 0,
                        'avg_open_seconds': 0.0,
                        'max_open_seconds': 0.0,
                        'total_open_seconds': 0.0
                    }
                
                return {
                    'total_openings': len(openings),
                    'avg_open_seconds': round(sum(openings) / len(openings), 2),
                    'max_open_seconds': round(max(openings), 2),
                    'total_open_seconds': round(sum(openings), 2)
                }
        except Error as e:
            print(f"[FridgeDatabase] Error calculating door statistics: {e}")
            return {
                'total_openings': 0,
                'avg_open_seconds': 0.0,
                'max_open_seconds': 0.0,
                'total_open_seconds': 0.0
            }
    
    def get_hourly_averages(self, fridge_id: int, hours: int = 168) -> List[Dict]:
        """
        Media temperatura/potenza per fascia oraria (0-23h)
        Utile per pattern detection
        
        Args:
            fridge_id: ID del frigo
            hours: Ore di storico da analizzare (default: 168 = 7 giorni)
        
        Returns:
            List[Dict]: [{
                'hour': 0-23,
                'avg_temperature': float,
                'avg_power': float,
                'sample_count': int
            }, ...]
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT 
                        HOUR(timestamp) as hour,
                        AVG(temperature) as avg_temperature,
                        AVG(power) as avg_power,
                        COUNT(*) as sample_count
                    FROM Measurements
                    WHERE fridge_ID = %s
                      AND timestamp >= NOW() - INTERVAL %s HOUR
                    GROUP BY HOUR(timestamp)
                    ORDER BY hour ASC
                """
                cursor.execute(query, (fridge_id, hours))
                results = cursor.fetchall()
                cursor.close()
                
                # Arrotonda valori
                for row in results:
                    if row['avg_temperature']:
                        row['avg_temperature'] = round(float(row['avg_temperature']), 2)
                    if row['avg_power']:
                        row['avg_power'] = round(float(row['avg_power']), 2)
                
                return results
        except Error as e:
            print(f"[FridgeDatabase] Error fetching hourly averages: {e}")
            return []
    
    def get_products_by_category_stats(self, fridge_id: int) -> List[Dict]:
        """
        Conteggio prodotti per categoria
        
        Args:
            fridge_id: ID del frigo
        
        Returns:
            List[Dict]: [{
                'category': str,
                'product_count': int,
                'total_quantity': int
            }, ...]
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT 
                        p.category,
                        COUNT(DISTINCT pf.product_ID) as product_count,
                        SUM(pf.quantity) as total_quantity
                    FROM ProductsFridge pf
                    JOIN Products p ON pf.product_ID = p.ID
                    WHERE pf.fridge_ID = %s
                      AND pf.removed_in IS NULL
                    GROUP BY p.category
                    ORDER BY total_quantity DESC
                """
                cursor.execute(query, (fridge_id,))
                results = cursor.fetchall()
                cursor.close()
                return results
        except Error as e:
            print(f"[FridgeDatabase] Error fetching product category stats: {e}")
            return []
    
    def get_most_consumed_products(self, fridge_id: int, limit: int = 10, days: int = 30) -> List[Dict]:
        """
        Prodotti più consumati nel periodo
        
        Args:
            fridge_id: ID del frigo
            limit: Numero massimo risultati
            days: Giorni da analizzare
        
        Returns:
            List[Dict]: [{
                'product_id': int,
                'name': str,
                'brand': str,
                'category': str,
                'total_consumed': int (quantità rimossa)
            }, ...]
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT 
                        p.ID as product_id,
                        p.name,
                        p.brand,
                        p.category,
                        SUM(ABS(pm.quantity)) as total_consumed
                    FROM ProductsMovements pm
                    JOIN Products p ON pm.product_ID = p.ID
                    WHERE pm.fridge_ID = %s
                      AND pm.quantity < 0
                      AND pm.timestamp >= NOW() - INTERVAL %s DAY
                    GROUP BY p.ID
                    ORDER BY total_consumed DESC
                    LIMIT %s
                """
                cursor.execute(query, (fridge_id, days, limit))
                results = cursor.fetchall()
                cursor.close()
                return results
        except Error as e:
            print(f"[FridgeDatabase] Error fetching most consumed products: {e}")
            return []
    
    def get_shopping_list(self, fridge_id: int, hours: int = 48) -> List[Dict]:
        """
        Prodotti finiti di recente (da ricomprare)
        
        Args:
            fridge_id: ID del frigo
            hours: Ore da considerare (default 48h)
        
        Returns:
            List[Dict]: [{
                'product_id': int,
                'name': str,
                'brand': str,
                'category': str,
                'finished_at': timestamp
            }, ...]
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT 
                        p.ID as product_id,
                        p.name,
                        p.brand,
                        p.category,
                        pf.removed_in as finished_at
                    FROM ProductsFridge pf
                    JOIN Products p ON pf.product_ID = p.ID
                    WHERE pf.fridge_ID = %s
                      AND pf.removed_in IS NOT NULL
                      AND pf.removed_in >= NOW() - INTERVAL %s HOUR
                    ORDER BY pf.removed_in DESC
                """
                cursor.execute(query, (fridge_id, hours))
                results = cursor.fetchall()
                cursor.close()
                return results
        except Error as e:
            print(f"[FridgeDatabase] Error fetching shopping list: {e}")
            return []
    
    def get_alert_statistics(self, fridge_id: int, days: int = 7) -> List[Dict]:
        """
        Statistiche alerts per categoria
        
        Args:
            fridge_id: ID del frigo
            days: Giorni da analizzare
        
        Returns:
            List[Dict]: [{
                'category': str,
                'count': int,
                'latest_timestamp': timestamp
            }, ...]
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT 
                        category,
                        COUNT(*) as count,
                        MAX(timestamp) as latest_timestamp
                    FROM Alerts
                    WHERE fridge_ID = %s
                      AND timestamp >= NOW() - INTERVAL %s DAY
                    GROUP BY category
                    ORDER BY count DESC
                """
                cursor.execute(query, (fridge_id, days))
                results = cursor.fetchall()
                cursor.close()
                return results
        except Error as e:
            print(f"[FridgeDatabase] Error fetching alert statistics: {e}")
            return []
