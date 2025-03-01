from sqlalchemy import BigInteger, ARRAY, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase,):
    __abstract__ = True


class User(Base):
    __tablename__ = "users"

    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    key_values: Mapped[list[str] | None] = mapped_column(ARRAY(String))

