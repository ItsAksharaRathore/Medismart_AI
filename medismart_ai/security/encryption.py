# security/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from utils.logger import get_logger

logger = get_logger(__name__)

class Encryptor:
    """End-to-end encryption for sensitive medical data"""
    
    def __init__(self, key_file=None, key_env_var="ENCRYPTION_KEY"):
        """
        Initialize encryption module
        
        Args:
            key_file: Path to file containing encryption key
            key_env_var: Environment variable name containing encryption key
        """
        self.key = self._load_or_generate_key(key_file, key_env_var)
        self.fernet = Fernet(self.key)
        logger.info("Encryption module initialized")
        
    def _load_or_generate_key(self, key_file, key_env_var):
        """
        Load existing key or generate a new one
        
        Args:
            key_file: Path to file containing key
            key_env_var: Environment variable name containing key
            
        Returns:
            bytes: Encryption key
        """
        # Try to load key from environment variable
        key = os.environ.get(key_env_var)
        if key:
            try:
                decoded_key = base64.urlsafe_b64decode(key)
                logger.info("Loaded encryption key from environment variable")
                return key.encode() if isinstance(key, str) else key
            except Exception:
                logger.warning(f"Invalid key format in environment variable {key_env_var}")
        
        # Try to load key from file
        if key_file and os.path.exists(key_file):
            try:
                with open(key_file, "rb") as f:
                    key = f.read().strip()
                logger.info(f"Loaded encryption key from file: {key_file}")
                return key
            except Exception as e:
                logger.error(f"Error loading key from file {key_file}: {str(e)}")
        
        # Generate new key
        logger.warning("No valid encryption key found, generating new key")
        return Fernet.generate_key()
        
    def encrypt(self, data):
        """
        Encrypt data
        
        Args:
            data: String or bytes to encrypt
            
        Returns:
            bytes: Encrypted data
        """
        try:
            if isinstance(data, str):
                data = data.encode()
                
            return self.fernet.encrypt(data)
            
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            raise
            
    def decrypt(self, encrypted_data):
        """
        Decrypt data
        
        Args:
            encrypted_data: Encrypted bytes
            
        Returns:
            bytes: Decrypted data
        """
        try:
            return self.fernet.decrypt(encrypted_data)
            
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            raise
            
    def generate_derived_key(self, salt, password):
        """
        Generate a key derived from a password
        
        Args:
            salt: Salt for key derivation
            password: Password for key derivation
            
        Returns:
            bytes: Derived key
        """
        try:
            if isinstance(password, str):
                password = password.encode()
                
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(password))
            return key
            
        except Exception as e:
            logger.error(f"Key derivation error: {str(e)}")
            raise
            
    def encrypt_field(self, data):
        """
        Encrypt a single field (with string conversion)
        
        Args:
            data: Data to encrypt
            
        Returns:
            str: Base64-encoded encrypted data
        """
        try:
            if data is None:
                return None
                
            # Convert to string if not already
            if not isinstance(data, (str, bytes)):
                data = str(data)
                
            encrypted = self.encrypt(data)
            return base64.urlsafe_b64encode(encrypted).decode()
            
        except Exception as e:
            logger.error(f"Field encryption error: {str(e)}")
            raise
            
    def decrypt_field(self, encrypted_data):
        """
        Decrypt a base64-encoded encrypted field
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            
        Returns:
            str: Decrypted data as string
        """
        try:
            if encrypted_data is None:
                return None
                
            decoded = base64.urlsafe_b64decode(encrypted_data)
            decrypted = self.decrypt(decoded)
            return decrypted.decode()
            
        except Exception as e:
            logger.error(f"Field decryption error: {str(e)}")
            raise
