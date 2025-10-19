from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET_KEY
from src.core.database import DatabaseService
from src.models.user import User


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=False,
)


class AuthService:
    """Сервис аутентификации и управления пользователями"""

    _BCRYPT_MAX_BYTES = 72

    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    def _normalize_password(self, password: str) -> str:
        """Обрезает пароль до 72 байт (ограничение bcrypt)."""
        if not isinstance(password, str):
            password = str(password)

        encoded = password.encode("utf-8")
        if len(encoded) <= self._BCRYPT_MAX_BYTES:
            return password

        truncated = encoded[: self._BCRYPT_MAX_BYTES]
        normalized = truncated.decode("utf-8", errors="ignore")

        while len(normalized.encode("utf-8")) > self._BCRYPT_MAX_BYTES:
            normalized = normalized[:-1]

        return normalized

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        normalized = self._normalize_password(plain_password)
        return pwd_context.verify(normalized, hashed_password)

    def hash_password(self, password: str) -> str:
        normalized = self._normalize_password(password)
        return pwd_context.hash(normalized)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        async with self.db_service.async_session() as session:
            stmt = select(User).where(User.email == email.lower())
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        async with self.db_service.async_session() as session:
            stmt = select(User).where(User.username == username)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        try:
            uuid_user_id = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
        except (TypeError, ValueError):
            return None

        async with self.db_service.async_session() as session:
            stmt = select(User).where(User.id == uuid_user_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def register_user(self, email: str, password: str, username: str) -> User:
        normalized_email = email.strip().lower()
        normalized_username = username.strip()

        existing_user = await self.get_user_by_email(normalized_email)
        if existing_user:
            raise ValueError("Пользователь с таким email уже существует")

        existing_username = await self.get_user_by_username(normalized_username)
        if existing_username:
            raise ValueError("Имя пользователя уже занято")

        hashed_password = self.hash_password(password)

        async with self.db_service.async_session() as session:
            user = User(
                email=normalized_email,
                username=normalized_username,
                hashed_password=hashed_password,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = await self.get_user_by_email(email.strip().lower())
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user

    def create_access_token(self, *, user_id: str, expires_delta: Optional[timedelta] = None) -> str:
        expire_delta = expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.now(timezone.utc) + expire_delta
        to_encode = {"sub": str(user_id), "exp": expire}
        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    async def get_user_from_token(self, token: str) -> Optional[User]:
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub")
            if user_id is None:
                return None
        except JWTError:
            return None

        return await self.get_user_by_id(user_id)
