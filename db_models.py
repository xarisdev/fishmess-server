from pydantic import BaseModel

class UserModel(BaseModel):
    login:          str
    username:       str

    id:             int | None = None
    avatar_id:      int | None = None

    status:         str = 'offline'