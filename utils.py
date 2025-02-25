import asyncio
from openai import AsyncOpenAI
import whisper
from config import Config

config = Config()


# rewrite in async
class VoiceHandler:
    def __init__(self):
        self.decode_model = whisper.load_model("base")

    def decode(self, fname: str) -> str:
        result = self.decode_model.transcribe(fname)
        return result['text']

    def encode(self):
        pass


class AIResponder:
    user_threads = {}

    async def init(self):
        self.client = AsyncOpenAI(
            api_key=config.openai.api_token
        )

        self.assistant = await self.client.beta.assistants.create(
            name="Chill Guy",
            instructions="Йоу! Будь чиловым!",
            model="gpt-4o-mini"
        )

        return self

    async def get_or_create_thread(self, tg_id: int) -> str:
        if tg_id not in self.user_threads:
            self.user_threads[tg_id] = (await self.client.beta.threads.create()).id
        return self.user_threads[tg_id]

    async def run_assistant(self, thread_id: str):
        runs = await self.client.beta.threads.runs.list(thread_id=thread_id)
        active_runs = [run for run in runs.data if run.status not in ["completed", "failed", "cancelled"]]

        if active_runs:
            for run in active_runs:
                await self.client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)

        run = await self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant.id
        )

        return run

    async def check_run_status(self, thread_id: str, run_id: str):
        while True:
            run = await self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )

            if run.status == "completed":
                break

            await asyncio.sleep(1)

    async def respond(self, tg_id: int, message: str):
        thread_id = await self.get_or_create_thread(tg_id)
        await self.client.beta.threads.messages.create(thread_id=thread_id, content=message, role="user")
        run = await self.run_assistant(thread_id=thread_id)
        await self.check_run_status(thread_id=thread_id, run_id=run.id)
        return (await self.client.beta.threads.messages.list(thread_id=thread_id)).data[0].content[0].text.value

    async def tts(self, text, fname):
        response = await self.client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )

        response.write_to_file(fname)