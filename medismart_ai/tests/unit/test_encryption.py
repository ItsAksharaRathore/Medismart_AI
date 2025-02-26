"""
Unit tests for encryption module.
"""
import unittest
import base64
from unittest.mock import patch
from security.encryption import EncryptionService

class TestEncryptionService(unittest.TestCase):
    """Test suite for EncryptionService."""
    
    def setUp(self):
        """Set up test cases."""
        self.encryption_service = EncryptionService("test_secret_key")
        self.test_data = "test_sensitive_data"
        self.test_json = {"name": "John Doe", "ssn": "123-45-6789"}
    
    def test_encrypt_decrypt_string(self):
        """Test encrypting and decrypting a string."""
        # Encrypt the test data
        encrypted_data = self.encryption_service.encrypt(self.test_data)
        
        # Verify it's different from the original
        self.assertNotEqual(encrypted_data, self.test_data.encode())
        
        # Decrypt and verify
        decrypted_data = self.encryption_service.decrypt_to_string(encrypted_data)
        self.assertEqual(decrypted_data, self.test_data)
    
    def test_encrypt_decrypt_json(self):
        """Test encrypting and decrypting JSON data."""
        # Encrypt the test JSON
        encrypted_data = self.encryption_service.encrypt(self.test_json)
        
        # Decrypt and verify
        decrypted_data = self.encryption_service.decrypt_to_json(encrypted_data)
        self.assertEqual(decrypted_data, self.test_json)
    
    def test_different_keys_produce_different_results(self):
        """Test that different keys produce different encryption results."""
        # Create a second encryption service with a different key
        second_service = EncryptionService("different_key")
        
        # Encrypt the same data with both services
        encrypted1 = self.encryption_service.encrypt(self.test_data)
        encrypted2 = second_service.encrypt(self.test_data)
        
        # Verify the encrypted data is different
        self.assertNotEqual(encrypted1, encrypted2)
    
    def test_encryption_consistency(self):
        """Test that encrypting the same data twice produces different results (due to IV/nonce)."""
        # Encrypt the same data twice
        encrypted1 = self.encryption_service.encrypt(self.test_data)
        encrypted2 = self.encryption_service.encrypt(self.test_data)
        
        # Verify the encrypted data is different (due to random IV/nonce)
        self.assertNotEqual(encrypted1, encrypted2)
        
        # But both decrypt to the same value
        decrypted1 = self.encryption_service.decrypt_to_string(encrypted1)
        decrypted2 = self.encryption_service.decrypt_to_string(encrypted2)
        self.assertEqual(decrypted1, decrypted2)
    
    def test_invalid_decryption(self):
        """Test handling invalid encrypted data."""
        # Try to decrypt invalid data
        with self.assertRaises(Exception):
            self.encryption_service.decrypt(b"invalid_encrypted_data")

if __name__ == '__main__':
    unittest.main()