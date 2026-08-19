from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.commands import RegisterUserCommand, RegisterUserHandler
from api.auth.exceptions import InvalidCredentialsError
from api.auth.queries import AuthenticateUserHandler, AuthenticateUserQuery
from api.auth.schemas import Token, UserRegister
from api.database import get_db
from api.users.exceptions import EmailAlreadyRegisteredError

router = APIRouter(prefix="/auth", tags=["auth"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: DbDep) -> Token:
    command = RegisterUserCommand(email=payload.email, password=payload.password)
    try:
        return await RegisterUserHandler(db).handle(command)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from exc


@router.post("/login", response_model=Token)
async def login(
    db: DbDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """`form_data.username` is the user's login, which is their email."""
    query = AuthenticateUserQuery(login=form_data.username, password=form_data.password)
    try:
        return await AuthenticateUserHandler(db).handle(query)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
