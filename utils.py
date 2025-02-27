import aiofiles
import os
from io import BytesIO
import openai
from config import Config

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

    async def run_assistant(self, thread_id: str):
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

        return run

    async def respond(self, tg_id: int, message: str) -> str:
        thread_id = await self.get_or_create_thread(tg_id)
        await self.client.beta.threads.messages.create(thread_id=thread_id, content=message, role="user")
        await self.run_assistant(thread_id=thread_id)
        return (await self.client.beta.threads.messages.list(thread_id=thread_id)).data[0].content[0].text.value

    async def tts(self, text: str, fname: str) -> None:
        response = await self.client.audio.speech.create(
            model=self.tts_model,
            voice="alloy",
            input=text
        )

        response.write_to_file(fname)

    async def decode(self, fname: str) -> str:
        async with aiofiles.open(fname, "rb") as f:
            content = BytesIO(await f.read())
            content.name = os.path.join(".", fname)
            transcription = await self.client.audio.transcriptions.create(file=content, model="whisper-1")

        return transcription.text
