# fishmess-server

- FastAPI
- websockets
- PostgreSQL

## Запуск
- Настройка окружения (python>=3.14.0)
- Установка зависимостей
```
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Переменные окружения
Файл .env
```
DATABASE_NAME=users
DATABASE_HOST=localhost
DATABASE_USER=postgres
DATABASE_PASS=postgres
DATABASE_PORT=5432
POOL_MIN_SIZE=1
POOL_MAX_SIZE=5
POOL_CTIMEOUT=60
```
Файл users.env (первые записи в бд)
```
USERNAMES=... ... ...
LOGINS=... ... ...
PASSWORDS=... ... ...
```

## API Documentation
Базовый URL: `http://localhost:8000`
Версия API: `v1`

### Авторизация
<details>
<summary><code>POST /auth/login</code> - Авторизация по логину и паролю</summary>

**Параметры запроса:**
| Название | Тип | Описание |
|----------|-----|----------|

**Параметры Headers:**
```json
{
    "Content-Type": "application/json"
}
```
**Параметры Body:**
```json
{
    "login": "string",
    "password": "string"
}
```
**Ответ JSON:**
```json
{
    "access_token": "string"
}
```
</details>

<details>
<summary><code>POST /auth/refresh_token</code> - Обновление токена доступа</summary>

**Параметры запроса:**
| Название | Тип | Описание |
|----------|-----|----------|

**Параметры Headers:**
```json
{
    "Authorization": "Bearer <access_token>"
}
```
**Параметры Body:**
```json
{}
```
**Ответ JSON:**
```json
{
    "access_token": "string"
}
```
</details>

## Работа с пользователем
<details>
<summary><code>GET /users/me или GET /users/{user_id}</code> - Возвращает информацию о пользователе</summary>

**Параметры запроса:**
| Название | Тип | Описание |
|----------|-----|----------|
| `user_id` | `int` | Идентификатор пользователя |

**Параметры Headers:**
```json
{
    "Authorization": "Bearer <access_token>"
}
```
**Параметры Body:**
```json
{}
```
**Ответ JSON:**
```json
{
    "data": {
        "id": "int",
        "avatar_id": "int | None",
        "login": "str",
        "username": "str",
        "status": "str"
    }
}
```
</details>

## Работа с чатами
<details>
<summary><code>GET /chats</code> - Получение списка чатов</summary>

**Параметры запроса:**
| Название | Тип | Описание |
|----------|-----|----------|

**Параметры Headers:**
```json
{
    "Authorization": "Bearer <access_token>"
}
```
**Параметры Body:**
```json
{}
```
**Ответ JSON:**
```json
{
    "chats_count": "int",
    "data": [
        {
            "id": "int",
            "avatar_id": "int | None",
            "name": "str",
            "first_user_id": "int",
            "second_user_id": "int",
            "last_msg_text": "str | None"
        },
        {...}
    ]
}
```
</details>
<details>
<summary><code>POST /chats</code> - Создание чата</summary>

**Параметры запроса:**
| Название | Тип | Описание |
|----------|-----|----------|

**Параметры Headers:**
```json
{
    "Content-Type": "application/json",
    "Authorization": "Bearer <access_token>"
}
```
**Параметры Body:**
```json
{
    "name": "string",
    "to_user_id": int
}
```
**Ответ JSON:**
```json
{
    "data": {
        "id": "int",
        "avatar_id": "int | None",
        "name": "str",
        "first_user_id": "int",
        "second_user_id": "int",
        "last_msg_text": "str | None",
    }
}
```
</details>

<details>
<summary><code>POST /chats/{chat_id}/messages</code> - Отправка сообщения</summary>

**Параметры запроса:**
| Название | Тип | Описание |
|----------|-----|----------|
| `chat_id` | `int` | Идентификатор чата |

**Параметры Headers:**
```json
{
    "Content-Type": "application/json",
    "Authorization": "Bearer <access_token>"
}
```
**Параметры Body:**
```json
{
    "text": "str"
}
```
**Ответ JSON:**
```json
{
    "data": {
        "id": "int",
        "text": "str",
        "chat_id": "int",
        "owner_id": "int"
    }
}
```
</details>

<details>
<summary><code>GET /chats/{chat_id}/messages?limit=50</code> - Получение истории сообщений</summary>

**Параметры запроса:**
| Название | Тип | Описание |
|----------|-----|----------|
| `chat_id` | `int` | Идентификатор чата |
| `limit` | `int` | Лимит истории сообщений |

**Параметры Headers:**
```json
{
    "Authorization": "Bearer <access_token>"
}
```
**Параметры Body:**
```json
{}
```
**Ответ JSON:**
```json
{
    "message_count": "int",
    "data": [
        {
            "id": "int",
            "text": "str",
            "chat_id": "int",
            "owner_id": "int"
        }
    ]
}
```
</details>

## Работа с файлами

## Базовые ошибки
| Номер ошибки | Имя | Описание |
|-------------------|------|-------------|
| 400 | Bad Request | Неверный запрос / Отсутствие данных |
| 401 | Unauthorized | Неверный логин или пароль / токен доступа |
| 403 | Forbidden | Доступ запрещен |
| 404 | Not Found | Ресурс не найден |
| 409 | Conflict | Конфликт с данными на сервере |
| 500 | Internal Server Error | Неожиданная ошибка на сервере |
| 503 | Service Unavailable | Сервер недоступен |
