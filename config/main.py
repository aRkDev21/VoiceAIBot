from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class ConfigBase(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class TelegramConfig(ConfigBase):
    model_config = SettingsConfigDict(env_prefix="tg_")

    bot_token: str


class OpenAIConfig(ConfigBase):
    model_config = SettingsConfigDict(env_prefix="openai_")

    api_token: str
    assistant_id: str


class DBConfig(ConfigBase):
    model_config = SettingsConfigDict(env_prefix="db_")

    url: str


class AmpConfig(ConfigBase):
    model_config = SettingsConfigDict(env_prefix="amp_")

    api_key: str


class RedisConfig(ConfigBase):
    model_config = SettingsConfigDict(env_prefix="redis_")

    user: str
    password: str
    user_password: str
    host: str
    num_db: int
    port: int


class Config(BaseSettings):
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    db: DBConfig = Field(default_factory=DBConfig)
    amp: AmpConfig = Field(default_factory=AmpConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
