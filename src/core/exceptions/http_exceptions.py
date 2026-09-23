from fastapi.exceptions import HTTPException
from fastcrud.exceptions.http_exceptions import(
    CustomException,
    BadRequestException,
    NotFoundException,
    ForbiddenException,
    UnauthorizedException,
    UnprocessableEntityException,
    DuplicateValueException,
    RateLimitException
)