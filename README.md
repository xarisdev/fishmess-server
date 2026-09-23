# fishmess-server

## Стек

- FastAPI + FastCRUD
- SQLAlchemy 2.0 (async) + SQLite (aiosqlite)
- JWT-Авторизация (access + refresh)
- Python >= 3.11

## Запуск

```bash
python -m venv .venv
source .venv/Scripts/activate    # source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env # Заполнить заглушку SECRET_KEY

uvicorn src.core.main:app --reload --port 8000
```

Сервер: http://localhost:8000

Swagger UI: http://localhost:8000/docs

OpenAPI JSON: http://localhost:8000/openapi.json

## Переменные окружения (.env)
```
APP_NAME=fishmess
SECRET_KEY=change-me-to-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
DATABASE_URL=sqlite+aiosqlite:///./database.db
```

## Base URL
```
http://localhost:8000/api/v1
```

## Авторизация

Схема: JWT Bearer. Access-токен живет 15 минут, refresh - 30 дней.
