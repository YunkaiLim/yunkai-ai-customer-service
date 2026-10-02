from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: str = Field(default="demo", min_length=1, max_length=512)


class ChatResponse(BaseModel):
    reply: str
    handoff: bool = False
    reason: str | None = None
    knowledge_score: float = 0.0
    sources: list[str] = Field(default_factory=list)


class KnowledgeHit(BaseModel):
    source: str
    content: str
    score: float


class LLMReply(BaseModel):
    answer: str
    confidence: Literal["high", "medium", "low"] = "medium"
    needs_human: bool = False
