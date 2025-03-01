from sqlalchemy import select, update
from database.database import connection
from database.models import User


@connection
async def get_user_by_tg(tg_id: int, session) -> User | None:
    stmt = select(User).where(User.tg_id == tg_id)
    result = await session.execute(stmt)
    return result.scalars().first()


@connection
async def edit_user(tg_id: int, session, **kwargs) -> None:
    stmt = update(User).where(User.tg_id == tg_id).values(**kwargs)
    await session.execute(stmt)
    await session.commit()


@connection
async def add_user(tg_id: int, session, **kwargs) -> User:
    new_user = User(tg_id=tg_id, **kwargs)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return new_user


