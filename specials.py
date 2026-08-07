import os
import shutil

from fastapi import UploadFile
from fastapi.responses import FileResponse

from secrets import token_urlsafe
from passlib.context import CryptContext

import logging
logging.basicConfig(
    level=logging.INFO,
    filename="managers.log",
    filemode="a",
    format="%(asctime)s %(levelname)s %(message)s"
)

from db_models import FileModel

class HashManager:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    @classmethod
    def hash_key(cls, secret_key: str) -> str:
        return cls.pwd_context.hash(secret_key)
    
    @classmethod
    def verify_key(cls, secret_key: str, hashed_key: str) -> bool:
        return cls.pwd_context.verify(secret_key, hashed_key)
    
    @staticmethod
    def generate_token(nbytes: int = 32) -> str:
        token = token_urlsafe(nbytes)
        return token
    
class FileManager:
    def __init__(self, mdir: str = "files", cdir: str = "files/cached"):
        self.main_path = os.path.join(mdir)
        self.cached_path = os.path.join(cdir)

        os.makedirs(self.main_path, exist_ok=True)
        os.makedirs(self.cached_path, exist_ok=True)

    def _404(self, path: str):
        error = 404, f"Path: {path} not exists"
        logging.error(error[1])
        return error
    
    def _201(self, detail: str):
        info = 201, f"Created: {detail}"
        logging.info(info[1])
        return info

    def save(self, file: UploadFile):
        logging.info(f"Saving file: {file.filename}")
        
        filename = file.filename
        _path = os.path.join(self.main_path, filename)
        with open(_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)

        if os.path.exists(_path):
            return self._201(filename) + (_path)
        
    def load(self, file: FileModel) -> FileResponse:
        logging.info(f"Search file {file.filename} for load")
        
        if not os.path.exists(file.filepath):
            return self._404(file.filepath)
        
        response = FileResponse(
            path=file.filepath,
            filename=file.filename,
            type='multipart/form-data'
        )
        return response