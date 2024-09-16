from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
from dotenv import load_dotenv
import os

# Load the .env file early on
load_dotenv("storeapi/.env")

class BaseConfig(BaseSettings):
    ENV_STATE: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # General settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"

    # PayPal settings
    PAYPAL_CLIENT_ID: Optional[str] = os.getenv("PAYPAL_CLIENT_ID")
    PAYPAL_SECRET: Optional[str] = os.getenv("PAYPAL_SECRET")

# Global configuration settings for all environments
class GlobalConfig(BaseConfig):
    DATABASE_URL: Optional[str] = None
    DB_FORCE_ROLL_BACK: bool = False
    KC_CLIENT_ID: Optional[str] = None
    KC_TOKEN_URL: Optional[str] = None
    KC_AUTH_URL: Optional[str] = None
    KC_REFRESH_URL: Optional[str] = None
    KC_CERTS_URL: Optional[str] = None

# Configuration settings for the development environment
class DevConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="DEV_")

# Configuration settings for the test environment
class TestConfig(GlobalConfig):
    DATABASE_URL: str = "sqlite:///test.db"
    DB_FORCE_ROLL_BACK: bool = True

    model_config = SettingsConfigDict(
        env_prefix="TEST_",
    )

# Cache the result of the function call to get the config from the .env file as it is only read once on startup
@lru_cache()
def get_config(env_state: Optional[str] = "dev"):
    """Instantiate config based on the environment."""
    configs = {
        "dev": DevConfig,
        "test": TestConfig,
    }
    return configs.get(env_state, DevConfig)()

# Load the .env file from the storeapi directory
print("Loading environment variables from .env...")

# Get the configuration for the current environment (default is "dev")
config = get_config(BaseConfig().ENV_STATE)

# Check that the PAYPAL_CLIENT_ID and PAYPAL_SECRET are loaded correctly
print(f"PAYPAL_CLIENT_ID: {config.PAYPAL_CLIENT_ID}")
print(f"PAYPAL_SECRET: {config.PAYPAL_SECRET}")
