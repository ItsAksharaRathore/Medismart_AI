
# api/middleware/security.py
from flask import request, jsonify, g
from security.encryption import decrypt_request
from security.access_control import verify_access
from security.hipaa import verify_hipaa_compliance
from utils.logger import get_logger

logger = get_logger(__name__)

def security_middleware():
    """Security middleware for request processing"""
    # Skip security checks for non-API routes
    if not request.path.startswith('/api'):
        return None
    
    # Extract API key or token from headers
    api_key = request.headers.get('X-API-Key')
    auth_token = request.headers.get('Authorization')
    
    if not api_key and not auth_token:
        logger.warning("Unauthorized access attempt")
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # Verify access rights
        user_info = verify_access(api_key, auth_token)
        if not user_info:
            return jsonify({"error": "Unauthorized"}), 401
            
        # Store user info in Flask's g object for downstream use
        g.user = user_info
        
        # For endpoints with sensitive data, verify HIPAA compliance
        if request.path.startswith('/api/prescriptions'):
            if not verify_hipaa_compliance(request, user_info):
                return jsonify({"error": "HIPAA compliance failure"}), 403
                
        # For encrypted requests, decrypt the payload
        if request.headers.get('X-Encrypted', 'false').lower() == 'true':
            try:
                decrypt_request(request)
            except Exception as e:
                logger.error(f"Decryption error: {str(e)}")
                return jsonify({"error": "Decryption failed"}), 400
                
        return None  # Continue processing the request
        
    except Exception as e:
        logger.error(f"Security middleware error: {str(e)}")
        return jsonify({"error": "Security check failed"}), 500

# === Core Business Logic ===
