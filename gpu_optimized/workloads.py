"""Small, repeatable workloads for decode and acceptance measurements."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Workload:
    name: str
    prompt: str
    max_tokens: int


CHAT = Workload(
    name="chat",
    prompt=(
        "Explain in detail how speculative decoding speeds up large language "
        "model inference, including tradeoffs."
    ),
    max_tokens=128,
)

DOCUMENT = Workload(
    name="document",
    prompt=(
        "Repeat the following document verbatim, exactly as written, with no additions:\n\n"
        + "The quick brown fox jumps over the lazy dog. " * 60
    ),
    max_tokens=256,
)


def select(name: str) -> list[Workload]:
    if name == "chat":
        return [CHAT]
    if name == "document":
        return [DOCUMENT]
    return [CHAT, DOCUMENT]
