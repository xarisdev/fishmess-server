from typing import Annotated

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends

from ...core.exceptions.http_exceptions import (
    DuplicateValueException,
    NotFoundException
)
from ..models import GetMultiResponse
from ...db.database import get_db
from ...crud.crud_chats import crud_chats
from ...models.chat import Chat, ChatCreate, ChatRead, ChatUpdate

router = APIRouter(prefix="/chats", tags=["Chats"])

@router.post("", response_model=ChatRead, status_code=201)
async def create_chat(
    chat: ChatCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    chat_exists = await crud_chats.exists(
        db=db,
        user_one_id=chat.user_one_id, 
        user_two_id=chat.user_two_id
    )
    if chat_exists:
        raise DuplicateValueException("Chat already exists")

    created_chat = await crud_chats.create(
        db=db,
        object=chat,
        return_as_model=True,
        schema_to_select=ChatRead
    )
    return created_chat

@router.get("/{id}", response_model=ChatRead)
async def get_chat(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    chat = await crud_chats.get(
        db=db,
        schema_to_select=ChatRead,
        return_as_model=True,
        one_or_none=True,
        id=id
    )
    if not chat:
        raise NotFoundException("Chat not found")

    return chat

@router.patch("/{id}", response_model=ChatRead)
async def update_chat(
    id: int,
    data: ChatUpdate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    chat_exists = await crud_chats.exists(db=db, id=id)
    if not chat_exists:
        raise NotFoundException("Chat not found")

    chat = await crud_chats.update(
        db=db,
        object=data,
        schema_to_select=ChatRead,
        return_as_model=True,
        id=id
    )
    return chat

@router.delete("/{id}", status_code=204)
async def delete_chat(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    chat_exists = await crud_chats.exists(db=db, id=id)
    if not chat_exists:
        raise NotFoundException("Chat not found")

    await crud_chats.delete(db=db, id=id)

    return None

# --- multi ---

@router.get("/{user_id}", response_model=GetMultiResponse[ChatRead])
async def get_chats_multi(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    condition = or_(
        Chat.user_one_id == user_id,
        Chat.user_two_id == user_id
    )
    chats = await crud_chats.get_multi(
        db=db,
        custom_filters=condition,
        schema_to_select=ChatRead,
        return_as_model=True
    )
    if not chats:
        raise NotFoundException("Chats not found")

    return chats