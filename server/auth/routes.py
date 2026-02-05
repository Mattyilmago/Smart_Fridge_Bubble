"""
Route Flask per autenticazione fridges
"""

from flask import Blueprint, request
from utils.logger import get_logger
from utils.errors import error_response, ErrorCode
from database import AuthQueries
from .jwt_utils import (
    generate_fridge_token,
    decode_fridge_token,
    decode_user_token,
    is_token_expiring_soon
)

logger = get_logger('auth')

# Blueprint per route auth
auth_bp = Blueprint('auth', __name__)

# Istanza AuthQueries (singleton)
db = AuthQueries(use_pool=True)


@auth_bp.route('/registerFridge', methods=['POST'])
def register_fridge():
    """
    Registra nuovo frigo
    
    Request JSON:
        {
            "user_token": "eyJ...",
            "position": "Cucina"
        }
    
    Response:
        Success (200): "eyJhbGc..." (solo token JWT)
        Error (400/401/404/500): {"success": false, "error": {...}}
    """
    try:
        data = request.get_json()
        
        # Validazione input
        if not data:
            logger.warning("Missing request body")
            return error_response(ErrorCode.INVALID_REQUEST, "Request body mancante")
        
        user_token = data.get('user_token')
        position = data.get('position')
        
        if not user_token:
            logger.warning("Missing user_token")
            return error_response(ErrorCode.MISSING_PARAMETER, "user_token mancante")
        
        if not position:
            logger.warning("Missing position")
            return error_response(ErrorCode.MISSING_PARAMETER, "position mancante")
        
        # Decodifica user token
        user_payload = decode_user_token(user_token)
        if not user_payload:
            logger.warning("Invalid user token")
            return error_response(ErrorCode.INVALID_USER_TOKEN)
        
        user_id = user_payload['user_id']
        
        # Verifica che utente esista
        if not db.user_exists(user_id):
            logger.warning(f"User {user_id} not found")
            return error_response(ErrorCode.USER_NOT_FOUND)
        
        # Crea frigo nel DB
        fridge_id = db.create_fridge(user_id, position)
        if not fridge_id:
            logger.error(f"Failed to create fridge for user {user_id}")
            return error_response(ErrorCode.DATABASE_ERROR, "Impossibile creare frigo")
        
        # Genera token frigo
        fridge_token = generate_fridge_token(fridge_id)
        
        logger.info(f"Frigo {fridge_id} registrato per user {user_id}, posizione: {position}")
        
        # Ritorna solo il token (come stringa, non JSON)
        return fridge_token, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in register_fridge: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@auth_bp.route('/isAuthorized', methods=['GET'])
def is_authorized():
    """
    Valida token frigo esistente
    - Se valido e non in scadenza: ritorna stesso token
    - Se valido ma in scadenza: ritorna nuovo token
    - Se scaduto: ritorna 401
    
    Query params:
        fridge_token: Token JWT da validare
    
    Response:
        Success (200): "eyJhbGc..." (token, stesso o rinnovato)
        Error (401): {"success": false, "error": {...}}
    """
    try:
        fridge_token = request.args.get('fridge_token')
        
        if not fridge_token:
            logger.warning("Missing fridge_token parameter")
            return error_response(ErrorCode.MISSING_PARAMETER, "fridge_token mancante")
        
        # Decodifica token
        payload = decode_fridge_token(fridge_token, verify_exp=True)
        
        if not payload:
            # Token scaduto o invalido
            logger.warning("Token expired or invalid")
            return error_response(ErrorCode.TOKEN_EXPIRED)
        
        fridge_id = payload['fridge_id']
        
        # Verifica se token sta per scadere
        if is_token_expiring_soon(payload):
            # Rinnova token
            new_token = generate_fridge_token(fridge_id)
            logger.info(f"Token rinnovato per frigo {fridge_id} (in scadenza)")
            return new_token, 200
        
        # Token ancora valido, ritorna stesso token
        logger.debug(f"Token valido per frigo {fridge_id}")
        return fridge_token, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in is_authorized: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)


@auth_bp.route('/renewFridge', methods=['POST'])
def renew_fridge():
    """
    Rinnova token frigo scaduto (chiamato dal Raspberry dopo input da app)
    
    Request JSON:
        {
            "user_token": "eyJ...",
            "fridge_id": 42
        }
    
    Response:
        Success (200): "eyJhbGc..." (nuovo token)
        Error (400/401/403/404/500): {"success": false, "error": {...}}
    """
    try:
        data = request.get_json()
        
        # Validazione input
        if not data:
            logger.warning("Missing request body")
            return error_response(ErrorCode.INVALID_REQUEST, "Request body mancante")
        
        user_token = data.get('user_token')
        fridge_id = data.get('fridge_id')
        
        if not user_token:
            logger.warning("Missing user_token")
            return error_response(ErrorCode.MISSING_PARAMETER, "user_token mancante")
        
        if not fridge_id:
            logger.warning("Missing fridge_id")
            return error_response(ErrorCode.MISSING_PARAMETER, "fridge_id mancante")
        
        # Decodifica user token
        user_payload = decode_user_token(user_token)
        if not user_payload:
            logger.warning("Invalid user token")
            return error_response(ErrorCode.INVALID_USER_TOKEN)
        
        user_id = user_payload['user_id']
        
        # Verifica ownership
        db_user_id = db.get_fridge_owner(fridge_id)
        
        if db_user_id is None:
            logger.warning(f"Frigo {fridge_id} non trovato")
            return error_response(ErrorCode.FRIDGE_NOT_FOUND)
        
        if db_user_id != user_id:
            logger.warning(f"Ownership mismatch: frigo {fridge_id} appartiene a user {db_user_id}, richiesto da {user_id}")
            return error_response(ErrorCode.OWNERSHIP_MISMATCH)
        
        # Genera nuovo token
        new_token = generate_fridge_token(fridge_id)
        
        logger.info(f"Token rinnovato per frigo {fridge_id} da user {user_id}")
        
        # Ritorna nuovo token
        return new_token, 200
        
    except Exception as e:
        logger.error(f"Unexpected error in renew_fridge: {e}")
        return error_response(ErrorCode.INTERNAL_ERROR)