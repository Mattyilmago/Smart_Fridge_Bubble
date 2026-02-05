"""
Route Flask per gestione utenti e fridges (lato utente)
"""

from flask import Blueprint, request
from utils.logger import get_logger
from utils.errors import error_response, ErrorCode
from utils.request_auth import require_user_token_from_query, require_user_token_from_json
from database import UserDatabase

logger = get_logger('users_api')

# Blueprint per route users
users_bp = Blueprint('users', __name__)

# Istanza UserDatabase (singleton)
db = UserDatabase(use_pool=True)


@users_bp.route('/fridges', methods=['GET'])
def get_user_fridges():
    """
    Recupera tutti i frighi di un utente
    
    Query params:
        user_token: Token JWT utente
    
    Response:
        Success (200): {
            "success": true,
            "fridges": [
                {
                    "ID": 1,
                    "position": "Cucina",
                    "created_at": "2026-01-15 10:30:00"
                },
                ...
            ]
        }
        Error (400/401/500): {"success": false, "error": {...}}
    """
    try:
        # Verifica e estrae user_id dal token
        result = require_user_token_from_query()
        if isinstance(result, tuple):
            return result
        user_id = result
        
        # Recupera frighi
        fridges = db.get_user_fridges(user_id)
        
        logger.info(f"Retrieved {len(fridges)} fridges for user {user_id}")
        
        return {
            "success": True,
            "fridges": fridges
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_user_fridges: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@users_bp.route('/fridge/<int:fridge_id>', methods=['GET'])
def get_fridge_info(fridge_id: int):
    """
    Recupera informazioni dettagliate di un frigo
    
    Query params:
        user_token: Token JWT utente
    
    Response:
        Success (200): {
            "success": true,
            "fridge": {
                "ID": 1,
                "user_ID": 42,
                "position": "Modena",
                "created_at": "2026-01-15 10:30:00"
            }
        }
        Error (400/401/403/404/500): {"success": false, "error": {...}}
    """
    try:
        # Verifica e estrae user_id dal token
        result = require_user_token_from_query()
        if isinstance(result, tuple):
            return result
        user_id = result
        
        # Verifica ownership
        if not db.verify_fridge_ownership(fridge_id, user_id):
            logger.warning(f"User {user_id} attempted to access fridge {fridge_id} (not owner)")
            return error_response(ErrorCode.OWNERSHIP_MISMATCH)
        
        # Recupera info frigo
        fridge = db.get_fridge_info(fridge_id)
        
        if not fridge:
            logger.warning(f"Fridge {fridge_id} not found")
            return error_response(ErrorCode.FRIDGE_NOT_FOUND)
        
        logger.info(f"Retrieved info for fridge {fridge_id}")
        
        return {
            "success": True,
            "fridge": fridge
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_fridge_info: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@users_bp.route('/fridge/<int:fridge_id>/position', methods=['PUT'])
def update_fridge_position(fridge_id: int):
    """
    Aggiorna la posizione di un frigo
    
    Request JSON:
        {
            "user_token": "eyJ...",
            "position": "Garage"
        }
    
    Response:
        Success (200): {
            "success": true,
            "message": "Posizione aggiornata"
        }
        Error (400/401/403/404/500): {"success": false, "error": {...}}
    """
    try:
        # Verifica e estrae user_id dal token
        result = require_user_token_from_json()
        if isinstance(result, tuple):
            return result
        user_id = result
        
        data = request.get_json()
        position = data.get('position')
        
        if not position:
            logger.warning("Missing position")
            return error_response(ErrorCode.MISSING_PARAMETER, "position mancante")
        
        # Verifica ownership
        if not db.verify_fridge_ownership(fridge_id, user_id):
            logger.warning(f"User {user_id} attempted to update fridge {fridge_id} (not owner)")
            return error_response(ErrorCode.OWNERSHIP_MISMATCH)
        
        # Aggiorna posizione
        success = db.update_fridge_position(fridge_id, position)
        
        if not success:
            logger.error(f"Failed to update position for fridge {fridge_id}")
            return error_response(ErrorCode.DATABASE_ERROR, "Impossibile aggiornare posizione")
        
        logger.info(f"Position updated for fridge {fridge_id}: {position}")
        
        return {
            "success": True,
            "message": "Posizione aggiornata"
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in update_fridge_position: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@users_bp.route('/fridge/<int:fridge_id>', methods=['DELETE'])
def delete_fridge(fridge_id: int):
    """
    Elimina un frigo
    
    Request JSON:
        {
            "user_token": "eyJ..."
        }
    
    Response:
        Success (200): {
            "success": true,
            "message": "Frigo eliminato"
        }
        Error (400/401/403/404/500): {"success": false, "error": {...}}
    """
    try:
        # Verifica e estrae user_id dal token
        result = require_user_token_from_json()
        if isinstance(result, tuple):
            return result
        user_id = result
        
        # Elimina frigo (verifica ownership dentro la funzione)
        success = db.delete_fridge(fridge_id, user_id)
        
        if not success:
            logger.warning(f"Failed to delete fridge {fridge_id} for user {user_id}")
            return error_response(ErrorCode.OWNERSHIP_MISMATCH, "Impossibile eliminare frigo")
        
        logger.info(f"Fridge {fridge_id} deleted by user {user_id}")
        
        return {
            "success": True,
            "message": "Frigo eliminato"
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in delete_fridge: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)

@users_bp.route('/statistics', methods=['GET'])
def get_user_statistics():
    """
    Recupera statistiche globali utente (tutti i frighi)
    
    Query params:
        user_token: Token JWT utente
    
    Response:
        Success (200): {
            "success": true,
            "statistics": {
                "total_fridges": 3,
                "total_measurements": 15234,
                "total_alerts": 42,
                "total_products": 18,
                "total_product_movements": 156
            }
        }
    """
    try:
        # Verifica e estrae user_id dal token
        result = require_user_token_from_query()
        if isinstance(result, tuple):
            return result
        user_id = result
        
        # Recupera statistiche
        stats = db.get_user_statistics(user_id)
        
        logger.info(f"Retrieved statistics for user {user_id}")
        
        return {
            "success": True,
            "statistics": stats
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_user_statistics: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@users_bp.route('/account', methods=['DELETE'])
def delete_user_account():
    """
    Elimina account utente (CASCADE elimina tutti i frighi e dati correlati)
    
    Request JSON:
        {
            "user_token": "eyJ..."
        }
    
    Response:
        Success (200): {
            "success": true,
            "message": "Account eliminato"
        }
    """
    try:
        # Verifica e estrae user_id dal token
        result = require_user_token_from_json()
        if isinstance(result, tuple):
            return result
        user_id = result
        
        # Elimina account
        success = db.delete_user_account(user_id)
        
        if not success:
            logger.warning(f"Failed to delete account for user {user_id}")
            return error_response(ErrorCode.DATABASE_ERROR, "Impossibile eliminare account")
        
        logger.info(f"Account deleted for user {user_id}")
        
        return {
            "success": True,
            "message": "Account eliminato con successo"
        }, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in delete_user_account: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)