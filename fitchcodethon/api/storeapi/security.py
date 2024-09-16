import logging
from typing import Annotated
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import jwt, jwk, ExpiredSignatureError, JWTError
import requests
from storeapi.config import config

logger = logging.getLogger(__name__)

# Configuration values from the config file
KC_CLIENT_ID: str = config.KC_CLIENT_ID
KC_TOKEN_URL: str = config.KC_TOKEN_URL
KC_AUTH_URL: str = config.KC_AUTH_URL
KC_REFRESH_URL: str = config.KC_REFRESH_URL
KC_CERTS_URL: str = config.KC_CERTS_URL
SECRET_KEY: str = config.SECRET_KEY  # Secret key for JWT encoding

# OAuth2 scheme for token-based authentication
oauth_2_scheme = OAuth2AuthorizationCodeBearer(
    tokenUrl=KC_TOKEN_URL,
    authorizationUrl=KC_AUTH_URL,
    refreshUrl=KC_REFRESH_URL,
)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Function to hash a password before storing it in the database
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Function to verify a plain password against a hashed password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Function to create a JWT access token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)  # Default expiration time
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

# Exception for invalid credentials
def create_credentials_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )

# Role validation function
def has_role(role_name: str):
    async def check_role(token_data: Annotated[dict, Depends(valid_access_token)]):
        roles = token_data.get("resource_access", {}).get("elbaapi", {}).get("roles", [])
        if role_name not in roles:
            logger.warning(f"Unauthorized access attempt with role: {role_name}")
            raise HTTPException(status_code=403, detail="Unauthorized access")
        logger.info(f"Role {role_name} validated successfully")
    return check_role

# Validating JWT Access Token
async def valid_access_token(access_token: Annotated[str, Depends(oauth_2_scheme)]):
    url = KC_CERTS_URL
    headers = {"User-agent": "custom-user-agent"}

    try:
        # Fetch the JWKs (JSON Web Key Set) from the Keycloak server
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        jwks = response.json()

        # Extract signing key from the fetched JWKs
        signing_key = jwk.construct(jwks["keys"][0])

        # Decode and validate JWT access token
        data = jwt.decode(
            access_token,
            signing_key,
            algorithms=["RS256"],
            audience=KC_CLIENT_ID,
            options={"verify_exp": True},
        )
        logger.info("Access token validated successfully")
        return data

    except ExpiredSignatureError as ex:
        logger.error("Access token has expired")
        raise create_credentials_exception("Token has expired") from ex
    except JWTError as ex:
        logger.error(f"Token validation failed: {str(ex)}")
        raise create_credentials_exception("Invalid token") from ex
    except requests.RequestException as ex:
        logger.error(f"Failed to fetch JWKs: {str(ex)}")
        raise HTTPException(status_code=500, detail="Failed to validate token")
