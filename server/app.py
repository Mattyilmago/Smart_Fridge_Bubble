"""
Smart Fridge Server - Entry Point
Server Flask per gestione autenticazione e dati fridges
"""

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config
from utils.logger import get_logger
from api.auth.routes import auth_bp
from api.users.routes import users_bp
from api.fridges.routes import fridges_bp
from api.debug.routes import debug_bp

# Logger
logger = get_logger('main')

# Crea app Flask
app = Flask(__name__)
app.config.from_object(Config)

# Rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=[f"{Config.RATE_LIMIT_IS_AUTHORIZED_PER_DAY} per day"]
)

# Applica rate limits specifici alle route auth
limiter.limit(f"{Config.RATE_LIMIT_REGISTER_PER_HOUR} per hour")(auth_bp.route('/registerFrigo'))
limiter.limit(f"{Config.RATE_LIMIT_RENEW_PER_HOUR} per hour")(auth_bp.route('/renewFrigo'))
limiter.limit(f"{Config.RATE_LIMIT_IS_AUTHORIZED_PER_DAY} per day")(auth_bp.route('/isAuthorized'))

# Registra blueprint
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(users_bp, url_prefix='/api/users')
app.register_blueprint(fridges_bp, url_prefix='/api/fridges')
app.register_blueprint(debug_bp, url_prefix='/api/debug')


@app.route('/')
def index():
    """Health check endpoint"""
    return {
        "service": "Smart Fridge Server",
        "status": "running",
        "version": "1.0.0"
    }, 200


@app.route('/health')
def health():
    """Health check dettagliato"""
    from database import UserDatabase
    
    db = UserDatabase()
    db_status = "ok" if db.test_connection() else "error"
    
    return {
        "status": "healthy",
        "database": db_status
    }, 200


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Smart Fridge Server - Starting...")
    logger.info("=" * 60)
    logger.info(f"Environment: {Config.FLASK_ENV}")
    logger.info(f"Debug: {Config.FLASK_DEBUG}")
    logger.info(f"Host: {Config.FLASK_HOST}:{Config.FLASK_PORT}")
    logger.info("=" * 60)
    
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )