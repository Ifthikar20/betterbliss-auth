# app/newsletter/crypto.py
import os
import base64
import secrets
import logging
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
import json

logger = logging.getLogger(__name__)

class SecureCrypto:
    def __init__(self):
        self.server_private_key = None
        self.server_public_key = None
        self._initialize_keys()
    
    def _initialize_keys(self):
        """Initialize or load server X25519 key pair"""
        try:
            # In production, load from secure storage or environment
            private_key_env = os.getenv('SERVER_PRIVATE_KEY_B64')
            
            if private_key_env:
                # Load existing key from environment
                private_key_bytes = base64.b64decode(private_key_env)
                self.server_private_key = x25519.X25519PrivateKey.from_private_bytes(private_key_bytes)
                logger.info("Loaded existing server private key from environment")
            else:
                # Generate new key pair
                self.server_private_key = x25519.X25519PrivateKey.generate()
                logger.info("Generated new server key pair")
                
                # Optionally save to environment for persistence
                private_bytes = self.server_private_key.private_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PrivateFormat.Raw,
                    encryption_algorithm=serialization.NoEncryption()
                )
                logger.warning(f"Save this private key to environment: SERVER_PRIVATE_KEY_B64={base64.b64encode(private_bytes).decode()}")
            
            self.server_public_key = self.server_private_key.public_key()
            
        except Exception as e:
            logger.error(f"Failed to initialize cryptographic keys: {e}")
            raise
    
    def get_public_key_bytes(self) -> str:
        """Get server public key as base64 string"""
        try:
            public_bytes = self.server_public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            return base64.b64encode(public_bytes).decode()
        except Exception as e:
            logger.error(f"Failed to export public key: {e}")
            raise
    
    async def decrypt_payload(self, encrypted_data: dict) -> dict:
        """Decrypt ChaCha20-Poly1305 encrypted payload"""
        try:
            # Extract encrypted components
            ciphertext = base64.b64decode(encrypted_data["ciphertext"])
            nonce = base64.b64decode(encrypted_data["nonce"])
            client_public_key_bytes = base64.b64decode(encrypted_data["clientPublicKey"])
            
            # Reconstruct client public key
            client_public_key = x25519.X25519PublicKey.from_public_bytes(client_public_key_bytes)
            
            # Perform ECDH key exchange
            shared_secret = self.server_private_key.exchange(client_public_key)
            
            # Derive encryption key using HKDF
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'\x00' * 32,  # Use proper random salt in production
                info=b'newsletter-encryption'
            )
            encryption_key = hkdf.derive(shared_secret)
            
            # Decrypt using ChaCha20-Poly1305
            cipher = ChaCha20Poly1305(encryption_key)
            plaintext = cipher.decrypt(nonce, ciphertext, None)
            
            # Parse JSON payload
            decrypted_data = json.loads(plaintext.decode())
            
            logger.info("Successfully decrypted newsletter payload")
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Payload decryption failed: {e}")
            raise ValueError(f"Decryption failed: {str(e)}")

# Global crypto instance
crypto_service = SecureCrypto()

def get_server_public_key() -> str:
    """Get server public key for client key exchange"""
    return crypto_service.get_public_key_bytes()

async def decrypt_payload(encrypted_data: dict) -> dict:
    """Decrypt encrypted payload from client"""
    return await crypto_service.decrypt_payload(encrypted_data)