import asyncio
import os

from aiogram import types, F, Router
from aiogram.types import Message, FSInputFile
from utils import AIResponder
import aiofiles

router = Router()

if not os.path.exists("downloads"):
    os.mkdir("downloads")


@router.message(F.voice)
async def answer_voice(message: Message, ai_responder: AIResponder):
    file_id = message.voice.file_id
    file = await message.bot.get_file(file_id)

    ogg_path = os.path.join("downloads", f"{file_id}.ogg")
    mp3_path = os.path.join("downloads", f"{file_id}.mp3")

    async with aiofiles.open(ogg_path, "wb") as f:
        await f.write((await message.bot.download_file(file.file_path)).read())

    text = await ai_responder.decode(ogg_path)

    answer = await ai_responder.respond(message.from_user.id, text)

    await ai_responder.tts(answer, mp3_path)
    await message.bot.send_voice(chat_id=message.from_user.id, voice=FSInputFile(mp3_path))

    await asyncio.gather(
        asyncio.to_thread(os.remove, ogg_path),
        asyncio.to_thread(os.remove, mp3_path)
    )
