import re
from pathlib import Path

from .models import KnowledgeHit


def _tokens(text: str) -> set[str]:
    text = text.lower()
    latin = re.findall(r"[a-z0-9_\-]{2,}", text)
    cjk = re.findall(r"[\u3400-\u9fff]", text)
    bigrams = ["".join(cjk[i:i + 2]) for i in range(max(0, len(cjk) - 1))]
    return set(latin + bigrams + cjk)


def _chunk_markdown(text: str, max_chars: int = 1400) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    output: list[str] = []
    buffer = ""
    for part in parts:
        candidate = f"{buffer}\n\n{part}".strip()
        if len(candidate) > max_chars and buffer:
            output.append(buffer)
            buffer = part
        else:
            buffer = candidate
    if buffer:
        output.append(buffer)
    return output


class KnowledgeBase:
    def __init__(self, directory: Path):
        self.directory = directory
        self.chunks: list[tuple[str, str, set[str]]] = []
        self.reload()

    def reload(self) -> int:
        self.directory.mkdir(parents=True, exist_ok=True)
        chunks: list[tuple[str, str, set[str]]] = []
        for path in sorted(self.directory.rglob("*.md")):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for chunk in _chunk_markdown(text):
                chunks.append((str(path.relative_to(self.directory)), chunk, _tokens(chunk)))
        self.chunks = chunks
        return len(chunks)

    def search(self, query: str, limit: int = 4) -> list[KnowledgeHit]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []
        scored: list[KnowledgeHit] = []
        for source, content, tokens in self.chunks:
            overlap = len(query_tokens & tokens)
            if overlap == 0:
                continue
            coverage = overlap / max(1, len(query_tokens))
            precision = overlap / max(1, len(tokens))
            score = 0.85 * coverage + 0.15 * min(1.0, precision * 8)
            scored.append(KnowledgeHit(source=source, content=content, score=round(score, 4)))
        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[:limit]
