from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends

from ..core.exceptions.http_exceptions import UnauthorizedException

from ..core.security import oauth2_scheme, verify_access_token
from ..db.database import get_db
from ..crud.crud_users import crud_users
from ..models.user import UserRead

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserRead:
    token_data = await verify_access_token(token, expected_type="access")
    if token_data is None:
        raise UnauthorizedException("Invalid token")

    user = await crud_users.get(
        db=db,
        schema_to_select=UserRead,
        return_as_model=True,
        one_or_none=True,
        id=token_data.user_id
    )
    if not user:
        raise UnauthorizedException("User not found")
    return user