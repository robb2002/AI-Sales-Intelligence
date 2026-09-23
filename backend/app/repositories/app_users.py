import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Text, Uuid, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.repositories.base import Base


class AppUser(Base):
    __tablename__ = "app_users"
    __table_args__ = (
        CheckConstraint("role IN ('SALES_REP', 'SALES_MANAGER')", name="app_users_role_check"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    clerk_user_id: Mapped[str] = mapped_column(Text, unique=True)
    email: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AppUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_clerk_user_id(self, clerk_user_id: str) -> AppUser | None:
        return await self._session.scalar(
            select(AppUser).where(AppUser.clerk_user_id == clerk_user_id)
        )

    async def upsert_from_clerk(self, clerk_user_id: str, email: str, role: str) -> AppUser:
        user = await self.get_by_clerk_user_id(clerk_user_id)
        if user is None:
            user = AppUser(clerk_user_id=clerk_user_id, email=email, role=role)
            self._session.add(user)
        else:
            user.email = email
            user.role = role
        await self._session.flush()
        return user
