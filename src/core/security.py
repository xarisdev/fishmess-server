from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
from fastapi.security import OAuth2PasswordBearer

from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.crud_users import crud_users
from .config import settings
from .schemas import TokenData

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    correct_password: bool = bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    return correct_password

def get_password_hash(password: str) -> str:
    hashed_password: str = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    return hashed_password

async def authenticate_user(username: str, password: str, db: AsyncSession) -> dict[str, Any] | Literal[False]:
    db_user = await crud_users.get(db=db, username=username)

    if not db_user:
        return False

    elif not await verify_password(password, db_user["password_hash"]):
        return False

    return db_user

async def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC).replace(tzinfo=None) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def create_refresh_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC).replace(tzinfo=None) + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def verify_access_token(
    token: str,
    expected_type: Literal["access", "refresh"] = "access"
) -> TokenData | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        sub = payload.get("sub")
        if sub is None:
            return None
        return TokenData(user_id=int(sub))

    except JWTError:
        return None