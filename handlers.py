import os
from io import BytesIO

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile

from utils import AIResponder, EventTracker
import database.requests as rq

router = Router()

if not os.path.exists("downloads"):
    os.mkdir("downloads")


@router.message(CommandStart())
async def start_message(message: Message, ai_responder: AIResponder, tracker: EventTracker):
    user = await rq.get_user_by_tg(message.from_user.id)
    if user is None:
        await rq.add_user(message.from_user.id)
        data = await ai_responder.tts(
            f"""Привет, {message.from_user.first_name}!
            Сейчас я могу:
            Вести с тобой диалог с помощью войсов и выделять твои основные ценности,
            а также понимать твоё настроение по фото"""
        )
        await message.bot.send_voice(chat_id=message.from_user.id, voice=BufferedInputFile(data, filename="hello.mp3"))
        tracker.user_reg(message.from_user.id)


@router.message(F.voice)
async def answer_voice(message: Message, ai_responder: AIResponder, tracker: EventTracker):
    tracker.user_voice(message.from_user.id)
    file_id = message.voice.file_id
    file = await message.bot.get_file(file_id)

    ogg_path = os.path.join("downloads", f"{file_id}.ogg")
    mp3_path = os.path.join("downloads", f"{file_id}.mp3")

    input_voice = BytesIO()
    await message.bot.download(file=file, destination=input_voice)
    text = await ai_responder.decode(input_voice, ogg_path)

    answer = await ai_responder.respond(message.from_user.id, text)
    output_voice = await ai_responder.tts(answer)
    await message.bot.send_voice(chat_id=message.from_user.id, voice=BufferedInputFile(output_voice, filename=mp3_path))


@router.message(F.photo)
async def anwer_photo(message: Message, ai_responder: AIResponder, tracker: EventTracker):
    tracker.user_photo(message.from_user.id)
    file_id = message.photo[-1].file_id
    mp3_path = os.path.join("downloads", f"{file_id}.mp3")
    file = await message.bot.get_file(file_id)
    photo = BytesIO()
    await message.bot.download(file=file, destination=photo)

    answer = await ai_responder.get_mood(photo)
    output_voice = await ai_responder.tts(answer)

    await message.bot.send_voice(chat_id=message.from_user.id, voice=BufferedInputFile(output_voice, filename=mp3_path))