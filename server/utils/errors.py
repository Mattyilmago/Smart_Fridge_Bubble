"""
Gestione errori standardizzata
"""

from enum import Enum
from flask import jsonify
from typing import Tuple


class ErrorCode(Enum):
    """Codici errore standardizzati"""
    
    # Auth errors (401)
    INVALID_USER_TOKEN = ("Token utente non valido o scaduto", 401)
    INVALID_FRIDGE_TOKEN = ("Token frigo non valido", 401)
    TOKEN_EXPIRED = ("Token scaduto, rinnovare tramite app", 401)
    
    # Permission errors (403)
    OWNERSHIP_MISMATCH = ("Frigo appartiene ad altro utente", 403)
    
    # Not found errors (404)
    USER_NOT_FOUND = ("Utente non trovato", 404)
    FRIDGE_NOT_FOUND = ("Frigo non trovato", 404)
    
    # Validation errors (400)
    MISSING_PARAMETER = ("Parametro mancante", 400)
    INVALID_POSITION = ("Posizione non valida", 400)
    INVALID_REQUEST = ("Richiesta non valida", 400)
    
    # Server errors (500)
    DATABASE_ERROR = ("Errore database, riprovare", 500)
    INTERNAL_ERROR = ("Errore interno del server", 500)


def error_response(error_code: ErrorCode, custom_message: str = None) -> Tuple[dict, int]:
    """
    Crea response di errore standardizzata
    
    Args:
        error_code: Codice errore da ErrorCode enum
        custom_message: Messaggio custom opzionale (override default)
    
    Returns:
        Tuple (json_response, http_status_code)
    
    Usage:
        return error_response(ErrorCode.TOKEN_EXPIRED)
        return error_response(ErrorCode.DATABASE_ERROR, "Connessione persa")
    """
    message, status_code = error_code.value
    
    if custom_message:
        message = custom_message
    
    response = {
        "success": False,
        "error": {
            "code": error_code.name,
            "message": message
        }
    }
    
    return jsonify(response), status_code