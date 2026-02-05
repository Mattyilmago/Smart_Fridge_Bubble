"""
Utility per gestione JWT (generazione e verifica token)
"""

import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
from config import Config
from utils.logger import get_logger

logger = get_logger('jwt')


def generate_fridge_token(fridge_id: int) -> str:
    """
    Genera token JWT per frigo
    
    Args:
        fridge_id: ID del frigo
    
    Returns:
        str: Token JWT firmato
    
    Example:
        token = generate_fridge_token(42)
        # "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    """
    payload = {
        'fridge_id': fridge_id,
        'exp': datetime.utcnow() + Config.FRIDGE_TOKEN_EXPIRY,
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(
        payload,
        Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM
    )
    
    logger.debug(f"Generated token for fridge {fridge_id}, expires: {payload['exp']}")
    return token


def decode_fridge_token(token: str, verify_exp: bool = True) -> Optional[Dict]:
    """
    Decodifica e verifica token JWT frigo
    
    Args:
        token: Token JWT da verificare
        verify_exp: Se True verifica scadenza (default), se False ignora
    
    Returns:
        Dict: Payload del token se valido, None se invalido
        Payload contiene: {'fridge_id': int, 'exp': timestamp, 'iat': timestamp}
    
    Example:
        payload = decode_fridge_token(token)
        if payload:
            fridge_id = payload['fridge_id']
    """
    try:
        options = {"verify_exp": verify_exp}
        payload = jwt.decode(
            token,
            Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM],
            options=options
        )
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning(f"Token expired")
        return None
        
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


def decode_user_token(token: str) -> Optional[Dict]:
    """
    Decodifica e verifica token JWT utente (dall'app)
    
    Args:
        token: Token JWT utente
    
    Returns:
        Dict: Payload con user_id, None se invalido
        Payload contiene: {'user_id': int, 'exp': timestamp, ...}
    
    Example:
        payload = decode_user_token(user_token)
        if payload:
            user_id = payload['user_id']
    """
    try:
        payload = jwt.decode(
            token,
            Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM]
        )
        
        # Verifica che contenga user_id
        if 'user_id' not in payload:
            logger.error("User token missing 'user_id' field")
            return None
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("User token expired")
        return None
        
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid user token: {e}")
        return None


def is_token_expiring_soon(payload: Dict) -> bool:
    """
    Verifica se token sta per scadere (entro RENEWAL_THRESHOLD giorni)
    
    Args:
        payload: Payload del token JWT
    
    Returns:
        bool: True se in scadenza, False altrimenti
    
    Example:
        payload = decode_fridge_token(token)
        if is_token_expiring_soon(payload):
            new_token = generate_fridge_token(payload['fridge_id'])
    """
    if 'exp' not in payload:
        return False
    
    exp_datetime = datetime.fromtimestamp(payload['exp'])
    time_remaining = exp_datetime - datetime.utcnow()
    
    return time_remaining < Config.RENEWAL_THRESHOLD