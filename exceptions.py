class ConflictError(Exception): # 409 - конфликт
    pass
class BadRequestError(Exception): # 400 - неверные данные
    pass
class NotFoundError(Exception): # 404
    pass
class DatabaseError(Exception): # 503 Service Unavailable / 500 - DataBase erorrs
    pass