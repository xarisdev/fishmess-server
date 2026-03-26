from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse

from pydantic import BaseModel

import asyncio
import json

# Для запуска сервера: uvicorn main:app --reload --port 8000

app = FastAPI(tittle='fishmess-server')
"""
@app.get('/ping')
def main():
    return {'status': 'OK'}"""

"""# Запрос к серверу по адресу
@app.get('/')
def root():
    return {"key": "Hello"}

# Запрос к серверу с параметрмами
@app.get('/{pk}') # Адрес /<pk>
def get_item(pk: int, q: str = None): # ?q=<value> где ?q - необязательный параметр + валидация
    return {"key": pk, "q": q}"""

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

class MessageRequest(BaseModel):
    message: str

@app.post("/send")
async def send_message_via_http(msg: MessageRequest):
    await manager.broadcast(msg.message)
    return {"status": "ok", "message": "Message broadcasted"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)