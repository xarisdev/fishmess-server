import logging
import psycopg2.errors as p2e

from secrets import token_urlsafe

from exceptions import *

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

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
    return token