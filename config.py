from os import getenv, path
from dotenv import load_dotenv

ENV = '.env'
USERS_ENV = 'users.env'

def load_env(env: str):
    if not path.exists(env):
        raise FileNotFoundError(f'Missing {env} file')
    load_dotenv(env)

def _get_env(key: str) -> str:
    value = getenv(key)
    if value is None:
        raise ValueError(f'Missing required envieroment variable: {key}')
    return value

load_env('.env')

DB_NAME     = _get_env('DATABASE_NAME')
DB_HOST     = _get_env('DATABASE_HOST')
DB_USER     = _get_env('DATABASE_USER')
DB_PORT     = int(_get_env('DATABASE_PORT'))
DB_PASSWORD = _get_env('DATABASE_PASS')

POOL_MIN_SIZE = int(_get_env('POOL_MIN_SIZE'))
POOL_MAX_SIZE = int(_get_env('POOL_MAX_SIZE'))
POOL_CTIMEOUT = int(_get_env('POOL_CTIMEOUT'))

DATABASE_POOL_CREATE = dict(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    min_size=POOL_MIN_SIZE,
    max_size=POOL_MAX_SIZE,
    command_timeout=POOL_CTIMEOUT
)

load_env('users.env')

USERS_LOGINS     = _get_env('LOGINS').split()
USERS_USERNAMES  = _get_env('USERNAMES').split()
USERS_PASSWORDS  = _get_env('PASSWORDS').split()
# Validation
if not (len(USERS_LOGINS) == len(USERS_USERNAMES) == len(USERS_PASSWORDS)) or len(USERS_LOGINS) == 0:
    raise ValueError(
        f'LOGINS ({len(USERS_LOGINS)}), USERNAMES ({len(USERS_USERNAMES)}) and PASSWORDS ({len(USERS_PASSWORDS)}) ' \
        'must have the same number of elements (n) and (n > 0)'
    ) 
DATABASE_USERS = (USERS_LOGINS, USERS_USERNAMES, USERS_PASSWORDS)