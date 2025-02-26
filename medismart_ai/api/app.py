
from flask import Flask
from flask_cors import CORS
from api.routes.prescription_routes import prescription_bp
from api.routes.drug_routes import drug_bp
from api.middleware.security import security_middleware
from utils.config import Config
from utils.logger import setup_logger

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    CORS(app)
    
    # Apply security middleware
    app.before_request(security_middleware)
    
    # Register blueprints
    app.register_blueprint(prescription_bp, url_prefix='/api/prescriptions')
    app.register_blueprint(drug_bp, url_prefix='/api/drugs')
    
    # Setup logging
    setup_logger(app)
    
    return app

# Run the application
if __name__ == "__main__":
    app = create_app()
    config = Config()
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
