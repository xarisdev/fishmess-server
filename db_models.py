from pydantic import BaseModel

class UserModel(BaseModel):
    login:          str
    username:       str

    id:             int | None = None
    avatar_id:      int | None = None

    status:         str = 'offline'

class ChatModel(BaseModel):
    id:             int
    avatar_id:      int | None = None
    
    name:           str

    first_user_id:  int
    second_user_id: int
    
    last_msg_text:  str | None = None