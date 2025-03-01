import aiofiles
import os
import json
from io import BytesIO

import openai

from config import Config
import database.requests as rq

config = Config()


class AIResponder:
    user_threads = {}

    async def init(self):
        self.client = openai.AsyncOpenAI(api_key=config.openai.api_token)
        self.assistant_id = config.openai.assistant_id
        self.asr_model = "whisper-1"
        self.tts_model = "tts-1"

        return self

    async def get_or_create_thread(self, tg_id: int) -> str:
        if tg_id not in self.user_threads:
            self.user_threads[tg_id] = (await self.client.beta.threads.create()).id
        return self.user_threads[tg_id]

    async def validate_value(self, value: str) -> bool:
        response = await self.client.chat.completions.create(
            model="o3-mini-2025-01-31",
            messages=[
                {"role": "system", "content": """Ты — валидатор ключевых ценностей. Твоя задача — проверить, является ли значение осмысленным и подходящим для ключевых ценностей человека. Если значение пустое, содержит бред или не является ключевой ценностью, верни False. Иначе верни True."""},
                {"role": "user", "content": f"Проверь значение: {value}"}
            ],
            tools=[{
                "type": "function",
                "function": {
                    "name": "validate_value",
                    "description": "Проверяет, является ли значение осмысленным и подходящим для ключевых ценностей.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "value": {
                                "type": "string",
                                "description": "Значение для проверки."
                            },
                            "is_valid": {
                                "type": "boolean",
                                "description": "True, если значение осмысленное и подходящее для ключевых ценностей, иначе False."
                            }
                        },
                        "required": ["value", "is_valid"]
                    }
                }
            }],
            tool_choice={"type": "function", "function": {"name": "validate_value"}}
        )

        tool_call = response.choices[0].message.tool_calls[0]
        arguments = json.loads(tool_call.function.arguments)
        return arguments["is_valid"]

    async def save_value(self, tg_id: int, value: str) -> bool:
        valid = await self.validate_value(value)
        if not valid:
            return False

        values = (await rq.get_user_by_tg(tg_id)).key_values or []
        if value not in values:
            values.append(value)

        await rq.edit_user(tg_id, key_values=values)
        return True

    async def run_assistant(self, thread_id: str, tg_id: int) -> str:
        runs = await self.client.beta.threads.runs.list(thread_id=thread_id)
        active_runs = [run for run in runs.data if run.status not in ["completed", "failed", "cancelled"]]

        if active_runs:
            for run in active_runs:
                await self.client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)

        run = await self.client.beta.threads.runs.create_and_poll(
            thread_id=thread_id,
            assistant_id=self.assistant_id,
            poll_interval_ms=1000
        )
        if run.status == "requires_action":
            tool_outputs = []
            for tool in run.required_action.submit_tool_outputs.tool_calls:
                if tool.function.name == "save_value":
                    value = json.loads(tool.function.arguments)['value']
                    is_saved = await self.save_value(tg_id, value)
                    tool_outputs.append({
                        "tool_call_id": tool.id,
                        "output": "Ценность сохранена" if is_saved else "Ценность не прошла валидацию"
                    })

            if tool_outputs:
                await self.client.beta.threads.runs.submit_tool_outputs_and_poll(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                    )

        elif run.status != "completed":
            return "Произошла ошибка. Пожалуйста, попробуйте позже."

        return (await self.client.beta.threads.messages.list(thread_id=thread_id)).data[0].content[0].text.value

    async def respond(self, tg_id: int, message: str) -> str:
        thread_id = await self.get_or_create_thread(tg_id)
        await self.client.beta.threads.messages.create(thread_id=thread_id, content=message, role="user")
        answer = await self.run_assistant(thread_id=thread_id, tg_id=tg_id)
        return answer

    async def tts(self, text: str) -> bytes:
        response = await self.client.audio.speech.create(
            model=self.tts_model,
            voice="alloy",
            input=text
        )

        return response.read()

    async def decode(self, fname: str) -> str:
        async with aiofiles.open(fname, "rb") as f:
            content = BytesIO(await f.read())
            content.name = os.path.join(".", fname)
            transcription = await self.client.audio.transcriptions.create(file=content, model="whisper-1")

        return transcription.text

