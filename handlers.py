import asyncio
import aiofiles
import os

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile

from utils import AIResponder
import database.requests as rq

router = Router()

if not os.path.exists("downloads"):
    os.mkdir("downloads")


@router.message(CommandStart())
async def start_message(message: Message, ai_responder: AIResponder):
    user = await rq.get_user_by_tg(message.from_user.id)
    if user is None:
        await rq.add_user(message.from_user.id)
        data = await ai_responder.tts(
            f"""Привет, {message.from_user.first_name}!
            Сейчас я могу:
            Вести с тобой диалог с помощью войсов и выделять твои основные ценности."""
        )
        await message.bot.send_voice(chat_id=message.from_user.id, voice=BufferedInputFile(data, filename="hello.mp3"))


@router.message(F.voice)
async def answer_voice(message: Message, ai_responder: AIResponder):
    file_id = message.voice.file_id
    file = await message.bot.get_file(file_id)

    ogg_path = os.path.join("downloads", f"{file_id}.ogg")
    mp3_path = os.path.join("downloads", f"{file_id}.mp3")

    # change it like send voice
    async with aiofiles.open(ogg_path, "wb") as f:
        await f.write((await message.bot.download_file(file.file_path)).read())

    text = await ai_responder.decode(ogg_path)
    answer = await ai_responder.respond(message.from_user.id, text)
    data = await ai_responder.tts(answer)
    await message.bot.send_voice(chat_id=message.from_user.id, voice=BufferedInputFile(data, filename=mp3_path))

    await asyncio.to_thread(os.remove, ogg_path)
