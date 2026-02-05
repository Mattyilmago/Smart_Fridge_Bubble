"""
Request Authentication Utilities
Funzioni helper per estrarre e validare token JWT da richieste HTTP.
Riduce duplicazione di codice nelle route users e fridges.
"""

from flask import request
from typing import Optional, Tuple, Union
from datetime import datetime
from utils.jwt_utils import decode_user_token, decode_fridge_token
from utils.errors import error_response, ErrorCode
from utils.logger import get_logger

logger = get_logger('auth_helpers')


def require_user_token_from_query() -> Union[int, Tuple]:
    """
    Estrae e valida user_token da query params
    
    Returns:
        int: user_id se token valido
        Tuple: (error_response, status_code) se errore
    
    Usage in route:
        result = require_user_token_from_query()
        if isinstance(result, tuple):
            return result  # Error response
        user_id = result
    """
    user_token = request.args.get('user_token')
    
    if not user_token:
        logger.warning("Missing user_token parameter")
        return error_response(ErrorCode.MISSING_PARAMETER, "user_token mancante")
    
    user_payload = decode_user_token(user_token)
    if not user_payload:
        logger.warning("Invalid user token")
        return error_response(ErrorCode.INVALID_USER_TOKEN)
    
    return user_payload['user_id']


def require_user_token_from_json() -> Union[int, Tuple]:
    """
    Estrae e valida user_token da JSON body
    
    Returns:
        int: user_id se token valido
        Tuple: (error_response, status_code) se errore
    
    Usage in route:
        result = require_user_token_from_json()
        if isinstance(result, tuple):
            return result  # Error response
        user_id = result
    """
    data = request.get_json()
    
    if not data:
        logger.warning("Missing request body")
        return error_response(ErrorCode.INVALID_REQUEST, "Request body mancante")
    
    user_token = data.get('user_token')
    
    if not user_token:
        logger.warning("Missing user_token")
        return error_response(ErrorCode.MISSING_PARAMETER, "user_token mancante")
    
    user_payload = decode_user_token(user_token)
    if not user_payload:
        logger.warning("Invalid user token")
        return error_response(ErrorCode.INVALID_USER_TOKEN)
    
    return user_payload['user_id']


def get_user_and_body() -> Union[Tuple[int, dict], Tuple]:
    """
    Estrae e valida user_token da JSON body, ritorna user_id E i dati JSON
    Utile quando servono altri parametri oltre al token
    
    Returns:
        Tuple[int, dict]: (user_id, data) se token valido
        Tuple: (error_response, status_code) se errore
    
    Usage in route:
        result = get_user_and_body()
        if len(result) == 2 and isinstance(result[1], dict) and 'success' not in result[1]:
            user_id, data = result
        else:
            return result  # Error response
    """
    data = request.get_json()
    
    if not data:
        logger.warning("Missing request body")
        return error_response(ErrorCode.INVALID_REQUEST, "Request body mancante")
    
    user_token = data.get('user_token')
    
    if not user_token:
        logger.warning("Missing user_token")
        return error_response(ErrorCode.MISSING_PARAMETER, "user_token mancante")
    
    user_payload = decode_user_token(user_token)
    if not user_payload:
        logger.warning("Invalid user token")
        return error_response(ErrorCode.INVALID_USER_TOKEN)
    
    return user_payload['user_id'], data


def require_fridge_token_from_query() -> Union[int, Tuple]:
    """
    Estrae e valida fridge_token da query params
    
    Returns:
        int: fridge_id se token valido
        Tuple: (error_response, status_code) se errore
    
    Usage in route:
        result = require_fridge_token_from_query()
        if isinstance(result, tuple):
            return result  # Error response
        fridge_id = result
    """
    fridge_token = request.args.get('fridge_token')
    
    if not fridge_token:
        logger.warning("Missing fridge_token parameter")
        return error_response(ErrorCode.MISSING_PARAMETER, "fridge_token mancante")
    
    payload = decode_fridge_token(fridge_token, verify_exp=True)
    if not payload:
        logger.warning("Invalid or expired fridge_token")
        return error_response(ErrorCode.INVALID_FRIDGE_TOKEN)
    
    return payload['fridge_id']


def require_fridge_token_from_json() -> Union[int, Tuple]:
    """
    Estrae e valida fridge_token da JSON body
    
    Returns:
        int: fridge_id se token valido
        Tuple: (error_response, status_code) se errore
    
    Usage in route:
        result = require_fridge_token_from_json()
        if isinstance(result, tuple):
            return result  # Error response
        fridge_id = result
    """
    data = request.get_json()
    
    if not data:
        logger.warning("Missing request body")
        return error_response(ErrorCode.INVALID_REQUEST, "Request body mancante")
    
    fridge_token = data.get('fridge_token')
    
    if not fridge_token:
        logger.warning("Missing fridge_token")
        return error_response(ErrorCode.MISSING_PARAMETER, "fridge_token mancante")
    
    payload = decode_fridge_token(fridge_token, verify_exp=True)
    if not payload:
        logger.warning("Invalid or expired fridge_token")
        return error_response(ErrorCode.INVALID_FRIDGE_TOKEN)
    
    return payload['fridge_id']


def parse_optional_timestamp(timestamp_str: Optional[str]) -> Union[Optional[datetime], Tuple]:
    """
    Parsing timestamp opzionale da stringa
    
    Args:
        timestamp_str: Timestamp in formato "YYYY-MM-DD HH:MM:SS" o None
    
    Returns:
        datetime: Oggetto datetime se valido
        None: Se timestamp_str è None
        Tuple: (error_response, status_code) se formato invalido
    
    Usage in route:
        timestamp_str = data.get('timestamp')
        result = parse_optional_timestamp(timestamp_str)
        if isinstance(result, tuple):
            return result  # Error response
        timestamp = result  # None o datetime
    """
    if not timestamp_str:
        return None
    
    try:
        return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        logger.warning(f"Invalid timestamp format: {timestamp_str}")
        return error_response(ErrorCode.INVALID_REQUEST, "Formato timestamp invalido (usa YYYY-MM-DD HH:MM:SS)")
