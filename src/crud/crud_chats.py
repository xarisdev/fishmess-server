from fastcrud import FastCRUD
from ..models.chat import Chat, ChatCreate, ChatRead, ChatUpdate

CRUDChats = FastCRUD[Chat, ChatCreate, ChatUpdate, ChatRead, dict, ChatUpdate]
crud_chats = CRUDChats(Chat)