import os

from secrets import token_urlsafe
from passlib.context import CryptContext

import logging

logging.basicConfig(
    level=logging.INFO,
    filename="managers.log",
    filemode="a",
    format="%(asctime)s %(levelname)s %(message)s"
)

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
    
class FileManager:
    def __init__(self, mdir: str = "files", cdir: str = "files/cached"):
        self.main_path = os.PathLike(mdir)
        self.cached_path = os.PathLike(cdir)

    def _404(self, path: str):
        error = 404, f"Path: {path} not exists"
        logging.error(error)
        return error

    def save(self, metadata: dict, file_obj):
        logging.info(f"")

    def load_for_name(self, filename: str, _cached: bool = True):
        _path = self.main_path
        if _cached:
            _path = self.cached_path

        path = os.PathLike(_path + filename)
        if not os.path.exists(path):
            return self._404(path)
        
        logging.info(f"Search for file: {path}")
        # Load

    def load_for_path(self, filepath: str):
        if not os.path.exists(filepath):
            return self._404(filepath)
        
        logging.info(f"Search for file: {filepath}")