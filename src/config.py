from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All config comes from environment variables (or .env file).

    Why pydantic-settings: validation + type coercion at startup, not buried
    inside route handlers. If VLLM_BASE_URL is missing or malformed, the app
    refuses to start rather than failing on the first request.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    vllm_base_url: str = Field(
        default="http://vllm:8000",
        description="Base URL of the vLLM service. Use the Docker service name, not localhost.",
    )
    vllm_model: str = Field(
        default="mock-model",
        description="Model name forwarded to vLLM. Must match the model loaded in the vLLM container.",
    )
