from fastapi import FastAPI

# Для запуска сервера: uvicorn main:app --reload

app = FastAPI()

# Запрос к серверу по адресу
@app.get('/')
def root():
    return {"key": "Hello"}

# Запрос к серверу с параметрмами
@app.get('/{pk}') # Адрес /<pk>
def get_item(pk: int, q: str = None): # ?q=<value> где ?q - необязательный параметр + валидация
    return {"key": pk, "q": q}