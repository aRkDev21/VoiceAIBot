import asyncio

from aiogram import Bot, Dispatcher

from config import Config
from handlers import router
from utils import AIResponder, EventTracker


async def main():
    config = Config()
    bot = Bot(token=config.telegram.bot_token)
    dp = Dispatcher()

    dp.include_router(router)

    ai_responder = await AIResponder().init()
    tracker = EventTracker()

    @dp.update.outer_middleware()
    async def inject_dependencies_middleware(handler, event, data):
        data["ai_responder"] = ai_responder
        data["tracker"] = tracker
        return await handler(event, data)

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")
