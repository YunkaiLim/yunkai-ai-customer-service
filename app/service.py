from .config import Settings
from .knowledge import KnowledgeBase
from .llm import OpenAICompatibleLLM
from .models import ChatResponse
from .policy import explicit_handoff_reason
from .storage import Storage


class SupportService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.storage = Storage(settings.db_path)
        self.kb = KnowledgeBase(settings.kb_dir)
        self.llm = OpenAICompatibleLLM(settings)

    async def answer(self, message: str, conversation_id: str) -> ChatResponse:
        history = self.storage.history(conversation_id, self.settings.max_history_messages)
        self.storage.add_message(conversation_id, "user", message)

        hard_reason = explicit_handoff_reason(message)
        hits = self.kb.search(message)
        best_score = hits[0].score if hits else 0.0

        if hard_reason:
            reply = "This request needs a human support agent for review."
            self.storage.add_message(conversation_id, "assistant", reply)
            return ChatResponse(
                reply=reply,
                handoff=True,
                reason=hard_reason,
                knowledge_score=best_score,
                sources=[hit.source for hit in hits],
            )

        try:
            llm_reply = await self.llm.generate(
                message=message,
                history=history,
                knowledge=[hit.model_dump() for hit in hits],
            )
        except Exception:
            reply = "The AI support service cannot handle this request reliably right now. A human should review it."
            self.storage.add_message(conversation_id, "assistant", reply)
            return ChatResponse(
                reply=reply,
                handoff=True,
                reason="llm_unavailable",
                knowledge_score=best_score,
                sources=[hit.source for hit in hits],
            )

        needs_human = llm_reply.needs_human
        reason = "model_requested_human_review" if needs_human else None
        if llm_reply.confidence == "low" and best_score < self.settings.handoff_score_threshold:
            needs_human = True
            reason = "low_confidence_or_missing_knowledge"

        self.storage.add_message(conversation_id, "assistant", llm_reply.answer)
        return ChatResponse(
            reply=llm_reply.answer,
            handoff=needs_human,
            reason=reason,
            knowledge_score=best_score,
            sources=[hit.source for hit in hits],
        )
