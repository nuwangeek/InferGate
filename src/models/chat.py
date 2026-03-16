from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    role: Annotated[
        str, Field(description="Role of the message sender (user, assistant, system)")
    ]
    content: Annotated[str, Field(description="Message content", max_length=32768)]


class ChatCompletionRequest(BaseModel):
    """Mirrors the OpenAI /v1/chat/completions request body.

    Why mirror OpenAI's schema: clients written for OpenAI work without changes,
    and vLLM's API is also OpenAI-compatible — so this model passes through
    cleanly in both directions.
    """

    model_config = ConfigDict(extra="ignore")  # silently drop unknown fields

    model: Annotated[str, Field(description="Model identifier")]
    messages: Annotated[
        list[Message],
        Field(description="Conversation messages", min_length=1),
    ]
    temperature: Annotated[
        float,
        Field(default=1.0, ge=0.0, le=2.0, description="Sampling temperature"),
    ] = 1.0
    max_tokens: Annotated[
        int | None,
        Field(default=None, ge=1, le=4096, description="Max tokens to generate"),
    ] = None
    stream: Annotated[
        bool, Field(default=False, description="Stream tokens via SSE")
    ] = False


class Choice(BaseModel):
    index: Annotated[int, Field(description="Index of this choice")]
    message: Message
    finish_reason: Annotated[str | None, Field(description="Why generation stopped")]


class Usage(BaseModel):
    prompt_tokens: Annotated[int, Field(description="Tokens in the prompt")]
    completion_tokens: Annotated[int, Field(description="Tokens in the completion")]
    total_tokens: Annotated[int, Field(description="Total tokens used")]


class ChatCompletionResponse(BaseModel):
    """Mirrors the OpenAI /v1/chat/completions response body."""

    id: Annotated[str, Field(description="Unique completion ID")]
    object: Literal["chat.completion"] = "chat.completion"
    created: Annotated[int, Field(description="Unix timestamp of creation")]
    model: Annotated[str, Field(description="Model used")]
    choices: Annotated[list[Choice], Field(description="Generated choices")]
    usage: Usage
