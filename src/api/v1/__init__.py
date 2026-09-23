from fastapi import APIRouter

from .users import router as users_router
from .chats import router as chats_router
from .login import router as login_router

router = APIRouter(prefix="/v1")
router.include_router(users_router)
router.include_router(chats_router)
router.include_router(login_router)