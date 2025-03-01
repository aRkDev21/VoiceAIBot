from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from config import Config

config = Config()
url = config.db.url
engine = create_async_engine(url=url)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


def connection(function):
    async def wrapper(*args, **kwargs):
        async with async_session_maker() as session:
            try:
                result = await function(*args, session=session, **kwargs)
                return result

            except Exception as e:
                await session.rollback()
                raise e

            finally:
                await session.close()
    return wrapper