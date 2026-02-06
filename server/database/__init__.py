"""
Database package per Smart Fridge

Classi stateless: il fridge_id viene passato come parametro.
Questo permette di gestire richieste concorrenti da frigo diversi.
"""

from .connection import DatabaseConfig, DatabaseConnection
from .fridge_db import FridgeDatabase
from .user_db import UserDatabase
from .debug_db import DebugDatabase

# Backward compatibility
DatabaseManager = FridgeDatabase
AuthQueries = UserDatabase

__all__ = [
    'DatabaseConfig',
    'DatabaseConnection', 
    'FridgeDatabase',
    'UserDatabase',
    'DebugDatabase',
    # Backward compatibility
    'DatabaseManager',
    'AuthQueries'
]
