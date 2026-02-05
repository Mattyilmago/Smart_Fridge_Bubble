"""
API package for Smart Fridge Server
"""
from .auth.routes import auth_bp
from .users.routes import users_bp
from .fridges.routes import fridges_bp

__all__ = ['auth_bp', 'users_bp', 'fridges_bp']
