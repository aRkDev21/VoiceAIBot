import base64
import os
import json
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

import openai
from amplitude import Amplitude, BaseEvent

from config import Config
import database.requests as rq

config = Config()


class AIResponder:
    async def init(self):
        self.client = openai.AsyncOpenAI(api_key=config.openai.api_token)
        self.assistant_id = config.openai.assistant_id
        self.asr_model = "whisper-1"
        self.tts_model = "tts-1"

        return self

    async def create_thread(self) -> str:
        return (await self.client.beta.threads.create(
            tool_resources=(await self.client.beta.assistants.retrieve(self.assistant_id)).tool_resources
        )).id

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

        message_content = (await self.client.beta.threads.messages.list(thread_id=thread_id)).data[0].content[0].text
        annotations = message_content.annotations
        for annotation in annotations:
            if file_citation := getattr(annotation, "file_citation", None):
                citied_file = await self.client.files.retrieve(file_citation.file_id)
                message_content.value = message_content.value.replace(
                    annotation.text, f"({citied_file.filename})"
                )

        return message_content.value

    async def respond(self, tg_id: int, message: str, thread_id: int = None) -> str:
        if thread_id is None:
            thread_id = await self.create_thread()
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

    async def decode(self, data: BytesIO, fname: str) -> str:
        data.name = os.path.join(".", fname)
        transcription = await self.client.audio.transcriptions.create(file=data, model="whisper-1")

        return transcription.text

    async def get_mood(self, data: BytesIO) -> str:
        base64_data = base64.b64encode(data.read()).decode()
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Какое настроение у человека на изображении?"
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64, {base64_data}", "detail": "high"},
                        }
                    ]
                }
            ]
        )

        return response.choices[0].message.content


class EventTracker:
    def __init__(self):
        self.client = Amplitude(config.amp.api_key)
        self.executor = ThreadPoolExecutor()

    def _track(self, event_type: str, tg_id: int):
        self.client.track(BaseEvent(event_type=event_type, user_id=str(tg_id)))

    def user_reg(self, tg_id: int):
        self.executor.submit(self._track, "New user", tg_id)

    def user_voice(self, tg_id: int):
        self.executor.submit(self._track, "Voice user", tg_id)

    def user_photo(self, tg_id: int):
        self.executor.submit(self._track, "Photo user", tg_id)

    def __del__(self):
        self.executor.shutdown(wait=True)
