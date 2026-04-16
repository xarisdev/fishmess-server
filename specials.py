from secrets import token_urlsafe
from passlib.context import CryptContext

class HashManager:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    @classmethod
    def hash_key(cls, plain_key: str) -> str:
        return cls.pwd_context.hash(plain_key)
    
    @classmethod
    def verify_key(cls, plain_key: str, hashed_key: str) -> bool:
        return cls.pwd_context.verify(plain_key, hashed_key)
    
    @staticmethod
    def generate_token() -> str:
        token = token_urlsafe(32)
        return token