from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends
from ..dependencies import get_current_user
from ...core.exceptions.http_exceptions import (
    DuplicateValueException,
    NotFoundException
)
from ...db.database import get_db
from ...crud.crud_users import crud_users
from ...models.user import UserCreate, UserCreateInternal, UserRead, UserUpdate
from ...core.security import get_password_hash

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("", response_model=UserRead, status_code=201)
async def create_user(
    user: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    user_exists = await crud_users.exists(db=db, username=user.username)
    if user_exists:
        raise DuplicateValueException("This username is not available")

    hashed_password = get_password_hash(user.password)
    user_internal = UserCreateInternal(
        username=user.username,
        password_hash=hashed_password,
        first_name=user.first_name,
        avatar_id=user.avatar_id
    )

    created_user = await crud_users.create(
        db=db,
        object=user_internal,
        schema_to_select=UserRead,
        return_as_model=True
    )
    return created_user

@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: Annotated[UserRead, Depends(get_current_user)]
):
    return current_user

@router.patch("/me", response_model=UserRead)
async def patch_me(
    user_data: UserUpdate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):    
    updated_user = await crud_users.update(
        db=db,
        object=user_data,
        id=current_user.id,
        schema_to_select=UserRead,
        return_as_model=True
    )
    return updated_user

@router.get("/{username}", response_model=UserRead)
async def get_user(
    username: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    user = await crud_users.get(
        db=db,
        schema_to_select=UserRead,
        return_as_model=True,
        one_or_none=True,
        username=username
    )
    if not user:
        raise NotFoundException("User not found")

    return user