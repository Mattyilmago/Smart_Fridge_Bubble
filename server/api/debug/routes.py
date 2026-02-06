"""
Route Flask per operazioni di debug/admin
Permette di visualizzare il contenuto delle tabelle del database
"""

from flask import Blueprint, request, jsonify
from utils.logger import get_logger
from utils.errors import error_response, ErrorCode
from database.debug_db import DebugDatabase

logger = get_logger('debug_api')

# Blueprint per route debug
debug_bp = Blueprint('debug', __name__)

# Istanza DebugDatabase per operazioni di debug
debug_db = DebugDatabase(use_pool=True)


@debug_bp.route('/table/<table_name>', methods=['GET'])
def get_table_data(table_name: str):
    """
    Recupera tutti i dati di una tabella (SELECT *)
    
    Path params:
        table_name: Nome della tabella (Users, Fridges, Measurements, etc.)
    
    Query params:
        limit: Numero massimo di righe da restituire (default: 100, max: 1000)
        offset: Offset per paginazione (default: 0)
    
    Response:
        Success (200): {
            "success": true,
            "table": "Users",
            "count": 42,
            "data": [
                {...},
                {...}
            ]
        }
        Error (400/500): {"success": false, "error": {...}}
    """
    try:
        # Parametri pagination
        try:
            limit = int(request.args.get('limit', 100))
            offset = int(request.args.get('offset', 0))
        except ValueError:
            return error_response(
                ErrorCode.INVALID_INPUT,
                "limit e offset devono essere numeri interi"
            )
        
        # Recupera dati usando il database layer
        rows = debug_db.get_table_data(table_name, limit, offset)
        
        if rows is None:
            return error_response(
                ErrorCode.INVALID_INPUT,
                f"Tabella non valida. Tabelle disponibili: {', '.join(debug_db.ALLOWED_TABLES)}"
            )
        
        logger.info(f"Recuperate {len(rows)} righe da tabella {table_name}")
        
        return jsonify({
            "success": True,
            "table": table_name,
            "count": len(rows),
            "limit": limit,
            "offset": offset,
            "data": rows
        }), 200
        
    except Exception as e:
        logger.error(f"Errore recupero dati tabella {table_name}: {e}")
        return error_response(
            ErrorCode.DATABASE_ERROR,
            f"Errore nel recupero dati: {str(e)}"
        )


@debug_bp.route('/tables', methods=['GET'])
def list_tables():
    """
    Elenca tutte le tabelle disponibili
    
    Response:
        Success (200): {
            "success": true,
            "tables": ["Users", "Fridges", ...]
        }
    """
    try:
        tables = debug_db.get_all_tables()
        
        if tables is None:
            return error_response(
                ErrorCode.DATABASE_ERROR,
                "Errore nel recupero delle tabelle"
            )
        
        return jsonify({
            "success": True,
            "tables": tables,
            "count": len(tables)
        }), 200
        
    except Exception as e:
        logger.error(f"Errore lista tabelle: {e}")
        return error_response(
            ErrorCode.DATABASE_ERROR,
            f"Errore nel recupero tabelle: {str(e)}"
        )


@debug_bp.route('/table/<table_name>/count', methods=['GET'])
def get_table_count(table_name: str):
    """
    Conta il numero di righe in una tabella
    
    Path params:
        table_name: Nome della tabella
    
    Response:
        Success (200): {
            "success": true,
            "table": "Users",
            "count": 42
        }
    """
    try:
        # Recupera conteggio usando il database layer
        count = debug_db.get_table_count(table_name)
        
        if count is None:
            return error_response(
                ErrorCode.INVALID_INPUT,
                f"Tabella non valida. Tabelle disponibili: {', '.join(debug_db.ALLOWED_TABLES)}"
            )
        
        return jsonify({
            "success": True,
            "table": table_name,
            "count": count
        }), 200
        
    except Exception as e:
        logger.error(f"Errore conteggio tabella {table_name}: {e}")
        return error_response(
            ErrorCode.DATABASE_ERROR,
            f"Errore nel conteggio: {str(e)}"
        )
