"""Send a prompt larger than 64K, then verify retrieval of a hidden code."""
from __future__ import annotations

import argparse
import os
import time

from .client import LlamaClient

SECRET = "739214"
PREFIX = f"The secret access code is {SECRET}.\n\n"
SUFFIX = (
    "\n\nQuestion: What is the secret access code?\n"
    "Answer with the number only.\nAnswer:"
)


def build_prompt(client: LlamaClient, target_tokens: int) -> tuple[str, int]:
    words = 4096
    phrase = "alpha beta gamma delta "
    prompt = PREFIX + phrase * words + SUFFIX
    count = 0
    for _ in range(4):
        tokens = client._request("/tokenize", {"content": prompt})
        count = len(tokens.get("tokens", []))
        if count >= target_tokens:
            break
        words = int(words * target_tokens / max(count, 1) * 1.05)
        prompt = PREFIX + phrase * words + SUFFIX
    return prompt, count


def main() -> None:
    parser = argparse.ArgumentParser(prog="gpu-context-check")
    parser.add_argument("--url", default="http://127.0.0.1:8081")
    parser.add_argument("--api-key", default=os.environ.get("LLAMA_API_KEY"))
    parser.add_argument("--target-tokens", type=int, default=70000)
    parser.add_argument("--max-tokens", type=int, default=24)
    parser.add_argument("--timeout", type=float, default=1200)
    args = parser.parse_args()

    client = LlamaClient(args.url, args.api_key, args.timeout)
    client.wait_ready()
    prompt, token_count = build_prompt(client, args.target_tokens)
    if token_count <= 65536:
        raise SystemExit(f"error: planned prompt has only {token_count} tokens")
    started = time.perf_counter()
    response, _ = client.complete(prompt, args.max_tokens)
    elapsed = time.perf_counter() - started
    timings = response.get("timings") or {}
    prompt_n = int(timings.get("prompt_n") or 0)
    if prompt_n <= 65536:
        raise SystemExit(f"error: server processed only {prompt_n} prompt tokens")
    text = (response.get("choices") or [{}])[0].get("text", "")
    print(f"tokenized_prompt={token_count} processed_prompt={prompt_n}")
    print(f"wall_seconds={elapsed:.1f} prefill_tps={timings.get('prompt_per_second', 0):.1f} "
          f"decode_tps={timings.get('predicted_per_second', 0):.1f}")
    print(f"response={text!r}")
    if SECRET not in text:
        raise SystemExit(f"error: expected secret {SECRET} in response")


if __name__ == "__main__":
    main()
