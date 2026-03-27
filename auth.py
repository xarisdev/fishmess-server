ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def generate_token() -> str:
    return "test_token:1"

def create_access_token() -> str:
    return generate_token()

def create_refresh_token() -> str:
    return generate_token()