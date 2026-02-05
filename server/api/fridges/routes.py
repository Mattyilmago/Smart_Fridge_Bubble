"""
Route Flask per operazioni frigo (measurements, alerts, products)
"""

from flask import Blueprint, request
from utils.logger import get_logger
from utils.errors import error_response, ErrorCode
from utils.request_auth import require_fridge_token_from_query, require_fridge_token_from_json, parse_optional_timestamp
from database import FridgeDatabase
from datetime import datetime

logger = get_logger('fridges_api')

# Blueprint per route fridges
fridges_bp = Blueprint('fridges', __name__)

# Istanza FridgeDatabase
db = FridgeDatabase(use_pool=True)


# ========================================
# MEASUREMENTS
# ========================================

@fridges_bp.route('/measurement', methods=['POST'])
def insert_measurement():
    """
    Inserisce nuova misurazione o batch di misurazioni (temperatura + potenza)
    
    Request JSON (singola misurazione):
        {
            "fridge_token": "eyJ...",
            "temperature": 4.5,
            "power": 120.3,
            "timestamp": "2026-02-05 14:30:00" (optional)
        }
    
    Request JSON (batch misurazioni):
        {
            "fridge_token": "eyJ...",
            "temperature": [4.5, 4.6, 4.7],
            "power": [120.3, 121.0, 119.5],
            "timestamp": ["2026-02-05 14:30:00", "2026-02-05 14:31:00", "2026-02-05 14:32:00"] (optional)
        }
    
    Response (singola):
        Success (201): {
            "success": true,
            "measurement_id": 123
        }
    
    Response (batch):
        Success (201): {
            "success": true,
            "measurement_ids": [123, 124, 125],
            "count": 3
        }
        
    Error (400/401/500): {"success": false, "error": {...}}
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_json()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        data = request.get_json()
        
        # Valida parametri
        temperature = data.get('temperature')
        power = data.get('power')
        
        if temperature is None:
            logger.warning("Missing temperature")
            return error_response(ErrorCode.MISSING_PARAMETER, "temperature mancante")
        
        if power is None:
            logger.warning("Missing power")
            return error_response(ErrorCode.MISSING_PARAMETER, "power mancante")
        
        # Determina se è batch o singola misurazione
        is_batch = isinstance(temperature, list)
        is_power_list = isinstance(power, list)
        
        # Validazione coerenza
        if is_batch != is_power_list:
            logger.warning("Temperature and power type mismatch")
            return error_response(ErrorCode.INVALID_REQUEST, 
                "temperature e power devono essere entrambi singoli o entrambi liste")
        
        # BATCH INSERT
        if is_batch:
            temperatures = temperature
            powers = power
            
            # Valida che abbiano stessa lunghezza
            if len(temperatures) != len(powers):
                logger.warning(f"Length mismatch: {len(temperatures)} temps vs {len(powers)} powers")
                return error_response(ErrorCode.INVALID_REQUEST, 
                    f"temperature e power devono avere stessa lunghezza (temp: {len(temperatures)}, power: {len(powers)})")
            
            if len(temperatures) == 0:
                logger.warning("Empty lists provided")
                return error_response(ErrorCode.INVALID_REQUEST, "Liste vuote non permesse")
            
            # Gestisci timestamp
            timestamp_data = data.get('timestamp')
            timestamps = None
            
            if timestamp_data is not None:
                if isinstance(timestamp_data, list):
                    if len(timestamp_data) != len(temperatures):
                        logger.warning(f"Timestamp length mismatch: {len(timestamp_data)} vs {len(temperatures)}")
                        return error_response(ErrorCode.INVALID_REQUEST, 
                            f"timestamp deve avere stessa lunghezza di temperature ({len(temperatures)})")
                    
                    # Parse ogni timestamp
                    timestamps = []
                    for i, ts in enumerate(timestamp_data):
                        result = parse_optional_timestamp(ts)
                        if isinstance(result, tuple):
                            logger.warning(f"Invalid timestamp at index {i}: {ts}")
                            return error_response(ErrorCode.INVALID_REQUEST, f"Timestamp invalido all'indice {i}")
                        timestamps.append(result)
                else:
                    # Singolo timestamp fornito per batch - errore
                    logger.warning("Single timestamp provided for batch insert")
                    return error_response(ErrorCode.INVALID_REQUEST, 
                        "Per batch insert, timestamp deve essere una lista o omesso")
            
            # Batch insert
            measurement_ids = db.insert_measurements_batch(fridge_id, temperatures, powers, timestamps)
            
            if not measurement_ids:
                logger.error(f"Failed to batch insert measurements for fridge {fridge_id}")
                return error_response(ErrorCode.DATABASE_ERROR, "Impossibile inserire misurazioni")
            
            logger.info(f"Batch inserted {len(measurement_ids)} measurements for fridge {fridge_id}")
            
            return {
                "success": True,
                "measurement_ids": measurement_ids,
                "count": len(measurement_ids)
            }, 201
        
        # SINGOLA MISURAZIONE
        else:
            # Timestamp opzionale
            result = parse_optional_timestamp(data.get('timestamp'))
            if isinstance(result, tuple):
                return result
            timestamp = result
            
            # Inserisci misurazione
            measurement_id = db.insert_measurement(fridge_id, temperature, power, timestamp)
            
            if not measurement_id:
                logger.error(f"Failed to insert measurement for fridge {fridge_id}")
                return error_response(ErrorCode.DATABASE_ERROR, "Impossibile inserire misurazione")
            
            logger.info(f"Measurement {measurement_id} inserted for fridge {fridge_id}")
            
            return {
                "success": True,
                "measurement_id": measurement_id
            }, 201
        
    except Exception as e:
        logger.error(f"Unexpected error in insert_measurement: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/measurements/history', methods=['GET'])
def get_measurements_history():
    """
    Recupera storico misurazioni
    
    Query params:
        fridge_token: Token JWT frigo
        hours: Numero ore storico (default: 48)
    
    Response:
        Success (200): {
            "success": true,
            "measurements": [
                {
                    "timestamp": "2026-02-05 14:30:00",
                    "temperature": 4.5,
                    "power": 120.3
                },
                ...
            ]
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        # Parametro hours (default 48)
        hours = request.args.get('hours', 48, type=int)
        
        # Recupera misurazioni
        measurements = db.get_measurements_history(fridge_id, hours)
        
        logger.info(f"Retrieved {len(measurements)} measurements for fridge {fridge_id}")
        
        return {
            "success": True,
            "measurements": measurements
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_measurements_history: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/measurements/temperature/stats', methods=['GET'])
def get_temperature_stats():
    """
    Recupera statistiche temperatura
    
    Query params:
        fridge_token: Token JWT frigo
        hours: Numero ore storico (default: vedi config)
    
    Response:
        Success (200): {
            "success": true,
            "stats": {
                "count": 100,
                "average": 4.2,
                "min": 3.8,
                "max": 5.1
            }
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        hours = request.args.get('hours', 48, type=int)
        
        # Recupera statistiche
        stats = db.get_temperature_statistics(fridge_id, hours)
        
        logger.info(f"Temperature stats for fridge {fridge_id}: {stats}")
        
        return {
            "success": True,
            "stats": stats
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_temperature_stats: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/measurements/power/stats', methods=['GET'])
def get_power_stats():
    """
    Recupera statistiche consumo
    
    Query params:
        fridge_token: Token JWT frigo
        hours: Numero ore storico (default: vedi config)
    
    Response:
        Success (200): {
            "success": true,
            "stats": {
                "count": 100,
                "average": 118.5,
                "min": 80.0,
                "max": 150.0
            }
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        from config import APIDefaults
        hours = request.args.get('hours', APIDefaults.POWER_STATS_HOURS, type=int)
        
        # Recupera statistiche
        stats = db.get_power_statistics(fridge_id, hours)
        
        logger.info(f"Power stats for fridge {fridge_id}: {stats}")
        
        return {
            "success": True,
            "stats": stats
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_power_stats: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


# ========================================
# ALERTS
# ========================================

@fridges_bp.route('/alert', methods=['POST'])
def insert_alert():
    """
    Inserisce nuovo alert
    
    Request JSON:
        {
            "fridge_token": "eyJ...",
            "category": "high_temp",
            "message": "Temperatura alta rilevata",
            "timestamp": "2026-02-05 14:30:00" (optional)
        }
    
    Response:
        Success (201): {
            "success": true,
            "alert_id": 456
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_json()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        data = request.get_json()
        
        # Valida parametri
        category = data.get('category')
        message = data.get('message')
        
        if not category:
            logger.warning("Missing category")
            return error_response(ErrorCode.MISSING_PARAMETER, "category mancante")
        
        if not message:
            logger.warning("Missing message")
            return error_response(ErrorCode.MISSING_PARAMETER, "message mancante")
        
        # Timestamp opzionale
        result = parse_optional_timestamp(data.get('timestamp'))
        if isinstance(result, tuple):
            return result
        timestamp = result
        
        # Inserisci alert
        alert_id = db.insert_alert(fridge_id, category, message, timestamp)
        
        if not alert_id:
            logger.error(f"Failed to insert alert for fridge {fridge_id}")
            return error_response(ErrorCode.DATABASE_ERROR, "Impossibile inserire alert")
        
        logger.info(f"Alert {alert_id} inserted for fridge {fridge_id}: {category}")
        
        return {
            "success": True,
            "alert_id": alert_id
        }, 201
        
    except Exception as e:
        logger.error(f"Unexpected error in insert_alert: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/alerts/recent', methods=['GET'])
def get_recent_alerts():
    """
    Recupera alert recenti
    
    Query params:
        fridge_token: Token JWT frigo
        hours: Numero ore storico (default: vedi config)
        category: Filtra per categoria (optional)
    
    Response:
        Success (200): {
            "success": true,
            "alerts": [
                {
                    "ID": 1,
                    "timestamp": "2026-02-05 14:30:00",
                    "category": "high_temp",
                    "message": "Temperatura alta"
                },
                ...
            ]
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        from config import APIDefaults
        hours = request.args.get('hours', APIDefaults.RECENT_ALERTS_HOURS, type=int)
        category = request.args.get('category')
        
        # Recupera alert
        alerts = db.get_recent_alerts(fridge_id, hours, category)
        
        logger.info(f"Retrieved {len(alerts)} alerts for fridge {fridge_id}")
        
        return {
            "success": True,
            "alerts": alerts
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_recent_alerts: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/alerts/critical', methods=['GET'])
def get_critical_alerts():
    """
    Recupera alert critici
    
    Query params:
        fridge_token: Token JWT frigo
        hours: Numero ore storico (default: 24)
    
    Response:
        Success (200): {
            "success": true,
            "alerts": [...]
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        from config import APIDefaults
        hours = request.args.get('hours', APIDefaults.CRITICAL_ALERTS_HOURS, type=int)
        
        # Recupera alert critici
        alerts = db.get_critical_alerts(fridge_id, hours)
        
        logger.info(f"Retrieved {len(alerts)} critical alerts for fridge {fridge_id}")
        
        return {
            "success": True,
            "alerts": alerts
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_critical_alerts: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/door', methods=['POST'])
def door_event():
    """
    Registra evento porta (aperta/chiusa)
    
    Request JSON:
        {
            "fridge_token": "eyJ...",
            "is_open": true
        }
    
    Response:
        Success (201): {
            "success": true,
            "alert_id": 789
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_json()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        data = request.get_json()
        
        # Valida parametro
        is_open = data.get('is_open')
        
        if is_open is None:
            logger.warning("Missing is_open")
            return error_response(ErrorCode.MISSING_PARAMETER, "is_open mancante")
        
        # Inserisci evento
        alert_id = db.insert_door_event(fridge_id, is_open)
        
        if not alert_id:
            logger.error(f"Failed to insert door event for fridge {fridge_id}")
            return error_response(ErrorCode.DATABASE_ERROR, "Impossibile inserire evento porta")
        
        logger.info(f"Door event for fridge {fridge_id}: {'open' if is_open else 'closed'}")
        
        return {
            "success": True,
            "alert_id": alert_id
        }, 201
        
    except Exception as e:
        logger.error(f"Unexpected error in door_event: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


# ========================================
# PRODUCTS
# ========================================

@fridges_bp.route('/product/movement', methods=['POST'])
def add_product_movement():
    """
    Registra movimento prodotto (aggiunta/rimozione)
    
    Request JSON:
        {
            "fridge_token": "eyJ...",
            "product_id": 5,
            "quantity": 2,
            "timestamp": "2026-02-05 14:30:00" (optional)
        }
    
    Response:
        Success (201): {
            "success": true,
            "movement_id": 321
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_json()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        data = request.get_json()
        
        # Valida parametri
        product_id = data.get('product_id')
        quantity = data.get('quantity')
        
        if product_id is None:
            logger.warning("Missing product_id")
            return error_response(ErrorCode.MISSING_PARAMETER, "product_id mancante")
        
        if quantity is None:
            logger.warning("Missing quantity")
            return error_response(ErrorCode.MISSING_PARAMETER, "quantity mancante")
        
        # Timestamp opzionale
        result = parse_optional_timestamp(data.get('timestamp'))
        if isinstance(result, tuple):
            return result
        timestamp = result
        
        # Inserisci movimento
        movement_id = db.add_product_movement(fridge_id, product_id, quantity, timestamp)
        
        if not movement_id:
            logger.error(f"Failed to insert product movement for fridge {fridge_id}")
            return error_response(ErrorCode.DATABASE_ERROR, "Impossibile inserire movimento prodotto")
        
        logger.info(f"Product movement {movement_id} for fridge {fridge_id}: product {product_id}, qty {quantity}")
        
        return {
            "success": True,
            "movement_id": movement_id
        }, 201
        
    except Exception as e:
        logger.error(f"Unexpected error in add_product_movement: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/products/current', methods=['GET'])
def get_current_products():
    """
    Recupera prodotti attualmente nel frigo
    
    Query params:
        fridge_token: Token JWT frigo
    
    Response:
        Success (200): {
            "success": true,
            "products": [
                {
                    "fridge_product_id": 1,
                    "product_id": 5,
                    "name": "Latte",
                    "brand": "Granarolo",
                    "category": "Latticini",
                    "quantity": 2,
                    "added_in": "2026-02-03 10:00:00"
                },
                ...
            ]
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        # Recupera prodotti
        products = db.get_current_products(fridge_id)
        
        logger.info(f"Retrieved {len(products)} products for fridge {fridge_id}")
        
        return {
            "success": True,
            "products": products
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_current_products: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/products/movements/history', methods=['GET'])
def get_movements_history():
    """
    Recupera storico movimenti prodotti
    
    Query params:
        fridge_token: Token JWT frigo
        hours: Numero ore storico (default: 168 = 7 giorni)
    
    Response:
        Success (200): {
            "success": true,
            "movements": [
                {
                    "ID": 1,
                    "timestamp": "2026-02-05 14:30:00",
                    "quantity": 2,
                    "name": "Latte",
                    "brand": "Granarolo",
                    "category": "Latticini"
                },
                ...
            ]
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        from config import APIDefaults
        hours = request.args.get('hours', APIDefaults.PRODUCT_MOVEMENTS_HOURS, type=int)
        
        # Recupera movimenti
        movements = db.get_product_movements_history(fridge_id, hours)
        
        logger.info(f"Retrieved {len(movements)} movements for fridge {fridge_id}")
        
        return {
            "success": True,
            "movements": movements
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_movements_history: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/product/search', methods=['GET'])
def search_product():
    """
    Cerca prodotto per nome (per YOLO detection)
    
    Query params:
        fridge_token: Token JWT frigo
        name: Nome prodotto da cercare
    
    Response:
        Success (200): {
            "success": true,
            "product": {
                "ID": 5,
                "name": "Latte",
                "brand": "Granarolo",
                "category": "Dairy"
            }
        }
        Not Found (404): {
            "success": false,
            "error": {...}
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        name = request.args.get('name')
        
        if not name:
            logger.warning("Missing name parameter")
            return error_response(ErrorCode.MISSING_PARAMETER, "name mancante")
        
        # Cerca prodotto
        product = db.get_product_by_name(name)
        
        if not product:
            logger.info(f"Product '{name}' not found")
            return error_response(ErrorCode.NOT_FOUND, "Prodotto non trovato"), 404
        
        logger.info(f"Product found: {product}")
        
        return {
            "success": True,
            "product": product
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in search_product: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)

# ========================================
# ADVANCED ANALYTICS
# ========================================

@fridges_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """
    Dashboard completa: ultimo dato, alert critici, prodotti, energia
    
    Query params:
        fridge_token: Token JWT frigo
    
    Response:
        Success (200): {
            "success": true,
            "dashboard": {
                "latest_measurement": {
                    "timestamp": "2026-02-05 14:30:00",
                    "temperature": 4.5,
                    "power": 120.3
                },
                "critical_alerts": [...],
                "product_count": 18,
                "energy_today_kwh": 2.45,
                "energy_today_cost": 0.61
            }
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        # Recupera dati dashboard
        latest = db.get_latest_measurement(fridge_id)
        critical_alerts = db.get_critical_alerts(fridge_id, hours=2)
        products = db.get_current_products(fridge_id)
        energy_kwh = db.calculate_energy_consumption(fridge_id, hours=24)
        energy_cost = db.calculate_energy_cost(fridge_id, hours=24)
        
        dashboard = {
            "latest_measurement": latest,
            "critical_alerts": critical_alerts,
            "product_count": len(products),
            "energy_today_kwh": energy_kwh,
            "energy_today_cost": energy_cost
        }
        
        logger.info(f"Dashboard retrieved for fridge {fridge_id}")
        
        return {
            "success": True,
            "dashboard": dashboard
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_dashboard: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/energy/consumption', methods=['GET'])
def get_energy_consumption():
    """
    Consumo energetico in kWh e costo stimato
    
    Query params:
        fridge_token: Token JWT frigo
        hours: Numero ore (default: 24)
        cost_per_kwh: Costo al kWh in euro (default: 0.25)
    
    Response:
        Success (200): {
            "success": true,
            "energy": {
                "hours": 24,
                "kwh": 2.45,
                "cost": 0.61,
                "cost_per_kwh": 0.25
            }
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        from config import APIDefaults
        hours = request.args.get('hours', APIDefaults.ENERGY_CONSUMPTION_HOURS, type=int)
        cost_per_kwh = request.args.get('cost_per_kwh', APIDefaults.ENERGY_COST_PER_KWH, type=float)
        
        # Calcola energia
        kwh = db.calculate_energy_consumption(fridge_id, hours)
        cost = db.calculate_energy_cost(fridge_id, hours, cost_per_kwh)
        
        logger.info(f"Energy consumption for fridge {fridge_id}: {kwh} kWh, cost {cost}€")
        
        return {
            "success": True,
            "energy": {
                "hours": hours,
                "kwh": kwh,
                "cost": cost,
                "cost_per_kwh": cost_per_kwh
            }
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_energy_consumption: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/energy/hourly-pattern', methods=['GET'])
def get_energy_hourly_pattern():
    """
    Pattern consumo per ora del giorno (0-23h)
    
    Query params:
        fridge_token: Token JWT frigo
        hours: Ore storico da analizzare (default: 168 = 7 giorni)
    
    Response:
        Success (200): {
            "success": true,
            "pattern": [
                {
                    "hour": 0,
                    "avg_temperature": 4.2,
                    "avg_power": 118.5,
                    "sample_count": 42
                },
                ...
            ]
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        hours = request.args.get('hours', 168, type=int)
        
        # Recupera pattern orario
        pattern = db.get_hourly_averages(fridge_id, hours)
        
        logger.info(f"Hourly pattern retrieved for fridge {fridge_id}")
        
        return {
            "success": True,
            "pattern": pattern
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_energy_hourly_pattern: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/temperature/trend', methods=['GET'])
def get_temperature_trend():
    """
    Trend temperatura (increasing/decreasing/stable)
    
    Query params:
        fridge_token: Token JWT frigo
        hours: Ore da analizzare (default: 6)
    
    Response:
        Success (200): {
            "success": true,
            "trend": "stable"  // o "increasing" o "decreasing"
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        from config import APIDefaults
        hours = request.args.get('hours', APIDefaults.TEMPERATURE_TREND_HOURS, type=int)
        
        # Calcola trend
        trend = db.get_temperature_trend(fridge_id, hours)
        
        logger.info(f"Temperature trend for fridge {fridge_id}: {trend}")
        
        return {
            "success": True,
            "trend": trend
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_temperature_trend: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/door/statistics', methods=['GET'])
def get_door_statistics():
    """
    Statistiche aperture porta
    
    Query params:
        fridge_token: Token JWT frigo
        hours: Ore da analizzare (default: 24)
    
    Response:
        Success (200): {
            "success": true,
            "statistics": {
                "total_openings": 15,
                "avg_open_seconds": 8.5,
                "max_open_seconds": 25.0,
                "total_open_seconds": 127.5
            }
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        hours = request.args.get('hours', 24, type=int)
        
        # Recupera statistiche porta
        stats = db.get_door_open_statistics(fridge_id, hours)
        
        logger.info(f"Door statistics for fridge {fridge_id}: {stats}")
        
        return {
            "success": True,
            "statistics": stats
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_door_statistics: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/products/shopping-list', methods=['GET'])
def get_shopping_list():
    """
    Lista prodotti finiti di recente (da ricomprare)
    
    Query params:
        fridge_token: Token JWT frigo
        hours: Ore da considerare (default: 48)
    
    Response:
        Success (200): {
            "success": true,
            "shopping_list": [
                {
                    "product_id": 5,
                    "name": "Latte",
                    "brand": "Granarolo",
                    "category": "dairy",
                    "finished_at": "2026-02-04 18:30:00"
                },
                ...
            ]
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        hours = request.args.get('hours', 48, type=int)
        
        # Recupera shopping list
        shopping_list = db.get_shopping_list(fridge_id, hours)
        
        logger.info(f"Shopping list retrieved for fridge {fridge_id}: {len(shopping_list)} items")
        
        return {
            "success": True,
            "shopping_list": shopping_list
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_shopping_list: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/products/statistics', methods=['GET'])
def get_product_statistics():
    """
    Statistiche prodotti: per categoria e più consumati
    
    Query params:
        fridge_token: Token JWT frigo
        days: Giorni per prodotti più consumati (default: 30)
        limit: Numero prodotti più consumati (default: 10)
    
    Response:
        Success (200): {
            "success": true,
            "statistics": {
                "by_category": [
                    {
                        "category": "dairy",
                        "product_count": 5,
                        "total_quantity": 12
                    },
                    ...
                ],
                "most_consumed": [
                    {
                        "product_id": 5,
                        "name": "Latte",
                        "brand": "Granarolo",
                        "category": "dairy",
                        "total_consumed": 15
                    },
                    ...
                ]
            }
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        from config import APIDefaults
        days = request.args.get('days', APIDefaults.MOST_CONSUMED_DAYS, type=int)
        limit = request.args.get('limit', APIDefaults.MOST_CONSUMED_LIMIT, type=int)
        
        # Recupera statistiche
        by_category = db.get_products_by_category_stats(fridge_id)
        most_consumed = db.get_most_consumed_products(fridge_id, limit, days)
        
        logger.info(f"Product statistics retrieved for fridge {fridge_id}")
        
        return {
            "success": True,
            "statistics": {
                "by_category": by_category,
                "most_consumed": most_consumed
            }
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_product_statistics: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@fridges_bp.route('/alerts/statistics', methods=['GET'])
def get_alert_statistics():
    """
    Statistiche alerts per categoria
    
    Query params:
        fridge_token: Token JWT frigo
        days: Giorni da analizzare (default: 7)
    
    Response:
        Success (200): {
            "success": true,
            "statistics": [
                {
                    "category": "door_open",
                    "count": 42,
                    "latest_timestamp": "2026-02-05 14:30:00"
                },
                ...
            ]
        }
    """
    try:
        # Verifica e estrae fridge_id dal token
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result
        fridge_id = result
        
        from config import APIDefaults
        days = request.args.get('days', APIDefaults.ALERT_STATISTICS_DAYS, type=int)
        
        # Recupera statistiche alert
        stats = db.get_alert_statistics(fridge_id, days)
        
        logger.info(f"Alert statistics retrieved for fridge {fridge_id}")
        
        return {
            "success": True,
            "statistics": stats
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_alert_statistics: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)