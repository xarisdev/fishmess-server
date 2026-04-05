import logging
import psycopg2.errors as p2e

from secrets import token_urlsafe

from datetime import datetime, timedelta

from exceptions import *

from passlib.context import CryptContext

from models import User

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def hash_api_key(plain_key: str) -> str: return pwd_context.hash(plain_key)
def verify_api_key(plain_key: str, hashed_key: str) -> bool: return pwd_context.verify(plain_key, hashed_key)

def handle_db_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except p2e.UniqueViolation as e:
            logger.error(f"Unique violation: {e}")
            raise ConflictError("Duplicate entry") from e
        except p2e.DataError as e:
            logger.error(f"Data error: {e}")
            raise BadRequestError("Invalid data") from e
        except p2e.OperationalError as e:
            logger.error(f"Operational error: {e}")
            raise DatabaseError("Database error") from e
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            raise DatabaseError("Internal error") from e
    return wrapper

def generate_refresh_token() -> str:
    token = token_urlsafe(32)
    hash_token = hash_api_key(token)
    return hash_token

def match_timestamp(timestamp: datetime, expired_after: timedelta) -> bool:
    return datetime.now() - timestamp < expired_after

def construct_user(user_data: dict) -> User:
    user = User(**user_data)
    return user