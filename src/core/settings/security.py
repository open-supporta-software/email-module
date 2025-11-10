from base64 import b64decode
from pathlib import Path
from typing import cast

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecuritySettings(BaseSettings):
    JWT_PRIVATE_KEY_BASE64: str = "generate_make_jwt-keygen"
    JWT_PUBLIC_KEY_BASE64: str = "generate_make_jwt-keygen"

    CSRF_COOKIE_NAME: str = "csrftoken"
    CSRF_EXPIRE_TIME: int = 86400 * 7
    CSRF_MIN_TOKEN_LENGTH: int = 30

    ALLOW_ORIGINS: list[str] = ["*"]
    ALLOW_HOSTS: list[str] = ["*"]

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ACCESS_TOKEN_ALGORITHM: str = "EdDSA"

    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    ALLOWED_IMAGE_TYPES: list[str] = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
        "image/tiff",
    ]

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parents[3] / ".env",
        extra="ignore",
        env_prefix="SECURITY_",
    )

    @property
    def decoded_private_key(self) -> ed25519.Ed25519PrivateKey:
        if self.JWT_PRIVATE_KEY_BASE64 == "generate_make_jwt-keygen":
            raise ValueError("Missing SECURITY_JWT_PRIVATE_KEY_BASE64 in environment")
        try:
            key_bytes = b64decode(self.JWT_PRIVATE_KEY_BASE64)
            key = serialization.load_pem_private_key(key_bytes, password=None)
            return cast(ed25519.Ed25519PrivateKey, key)
        except ValueError as e:
            raise ValueError("Invalid private key format or Base64 data") from e

    @property
    def decoded_public_key(self) -> ed25519.Ed25519PublicKey:
        if self.JWT_PUBLIC_KEY_BASE64 == "generate_make_jwt-keygen":
            raise ValueError("Missing SECURITY_JWT_PUBLIC_KEY_BASE64 in environment")
        try:
            key_bytes = b64decode(self.JWT_PUBLIC_KEY_BASE64)
            key = serialization.load_pem_public_key(key_bytes)
            return cast(ed25519.Ed25519PublicKey, key)
        except ValueError as e:
            raise ValueError("Invalid public key format or Base64 data") from e
