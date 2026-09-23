from fastcrud import FastCRUD

from ..models.user import User, UserCreateInternal, UserUpdate, UserRead

CRUDUser = FastCRUD[User, UserCreateInternal, UserUpdate, UserRead, dict, UserUpdate]
crud_users = CRUDUser(User)