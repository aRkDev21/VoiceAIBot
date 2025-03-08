import asyncio
import openai
from config import Config

config = Config()
client = openai.AsyncOpenAI(api_key=config.openai.api_token)
tool = {
    "type": "function",
    "function": {
        "name": "save_value",
        "description": "Сохраняет одну жизненную ценность в базу данных.",
        "parameters": {
            "type": "object",
            "properties": {
                "value": {
                    "type": "string",
                    "description": "Какая-либо из жизненных ценностей. Например: близкие, общение, любовь и так далее."
                }
            },
            "required": ["value"],
            "additionalProperties": False,
        },
        "strict": True
        }
    }


async def create_assistant():
    ass = await client.beta.assistants.create(
        name="Psychologist",
        model="o3-mini-2025-01-31",
        instructions="""Ты — дружелюбный и внимательный помощник, который помогает людям понять их ключевые ценности.
        Твоя задача — задавать вопросы, слушать ответы пользователя и анализировать их, чтобы определить,что для него важно в жизни.
        ### Как работать:
        1. Обьясни пользователю, что ты хочешь помочь ему с поиском его жизненных ценнностей.
        2. Задавай открытые вопросы, чтобы узнать, что важно для пользователя. Например:
        - Что для тебя самое важное в жизни?
        - Какие принципы или идеи ты считаешь незыблемыми?
        - Что вдохновляет тебя и придает смысл твоей жизни?
        - Какие качества ты больше всего ценишь в людях?
        3. Анализируй ответы пользователя и выделяй ключевые ценности.
        Например, если пользователь говорит, что для него важны семья, здоровье и честность, выдели эти ценности.
        4. Если нужно, задавай уточняющие вопросы, чтобы лучше понять пользователя.
        5. Когда одна какая-либо ценность будет определена, вызови функцию `save_value` для её сохранения.
        6. Если ты получишь в ответ то, что ценность определена неверно, повтори всё тоже самое, не бойся ошибаться.""",
        tools=[tool]
    )

    print(ass.id)


async def update_assistant():
    vector_store = await client.beta.vector_stores.create(name="Anxiety FAQ")
    f = open("Anxiety.docx", "rb")
    file_batch = await client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id, files=[f])
    print(file_batch.status)
    print(file_batch.file_counts)

    await client.beta.assistants.update(
        assistant_id=config.openai.assistant_id,
        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
        tools=[{"type": "file_search"}, tool]
    )

asyncio.run(update_assistant())
