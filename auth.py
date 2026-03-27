ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def generate_token(token) -> str:
    return f"{token}:1"

def create_access_token(token) -> str:
    return generate_token(token)

def create_refresh_token(token) -> str:
    return generate_token(token)