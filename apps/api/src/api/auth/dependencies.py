from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.security import decode_access_token
from api.database import get_db
from api.users.models import User
from api.users.queries import GetUserByIdHandler, GetUserByIdQuery

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

_credentials_exception = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    "Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        user_id = decode_access_token(token)
    except jwt.InvalidTokenError as exc:
        raise _credentials_exception from exc

    user = await GetUserByIdHandler(db).handle(GetUserByIdQuery(user_id=int(user_id)))
    if user is None:
        raise _credentials_exception
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
