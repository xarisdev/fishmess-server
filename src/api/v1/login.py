from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.database import get_db
from ...core.exceptions.http_exceptions import UnauthorizedException
from ...core.schemas import Token
from ...core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    verify_access_token,
)

router = APIRouter(tags=["login"])

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, str]:
    user = await authenticate_user(username=form_data.username, password=form_data.password, db=db)
    if not user:
        raise UnauthorizedException("Wrong username or password")

    access_token_expire = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(data={"sub": str(user["id"])}, expires_delta=access_token_expire)
    refresh_token = await create_refresh_token(data={"sub": str(user["id"])})

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

from ..models import RefreshRequest

@router.post("/refresh", response_model=Token)
async def refresh_access_token(payload: RefreshRequest) -> dict[str, str]:
    token_data = await verify_access_token(payload.refresh_token, expected_type="refresh")
    if token_data is None:
        raise UnauthorizedException("Invalid token")

    new_access_token = await create_access_token(data={"sub": str(token_data.user_id)})
    return {"access_token": new_access_token, "token_type": "bearer"}