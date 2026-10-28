# Harness integration

Any client that supports an OpenAI-compatible chat endpoint can connect.

```text
Base URL: https://llm.glicc.id/v1
Model:    qwen3.8-moe
Context:  262,144
Tools:    yes
Vision:   yes
```

Create a key at `https://llminferences.glicc.id/keys`.

## curl

```bash
export GLICC_API_KEY="gk_..."

curl https://llm.glicc.id/v1/chat/completions \
  -H "Authorization: Bearer $GLICC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.8-moe",
    "messages": [{"role": "user", "content": "Say ok"}],
    "max_tokens": 16,
    "temperature": 0
  }'
```

## OpenAI Python SDK

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://llm.glicc.id/v1",
    api_key=os.environ["GLICC_API_KEY"],
)

response = client.chat.completions.create(
    model="qwen3.8-moe",
    messages=[{"role": "user", "content": "Explain KV cache in 3 bullets."}],
    max_tokens=512,
)
print(response.choices[0].message.content)
```

Streaming uses the same client with `stream=True`.

## oh-my-pi

`~/.omp/profiles/glicc/agent/models.yml`:

```yaml
providers:
  glicc:
    baseUrl: https://llm.glicc.id/v1
    api: openai-completions
    apiKey: GLICC_API_KEY
    authHeader: true
    models:
      - id: qwen3.8-moe
        name: Glicc Qwen3.8 MoE
        reasoning: true
        supportsTools: true
        input: [text, image]
        contextWindow: 256000
        maxContextWindow: 256000
        maxTokens: 8192
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 }
        compat:
          supportsReasoningEffort: true
          thinkingFormat: qwen-chat-template
          qwenTemplateReasoningEffort: true
          reasoningContentField: reasoning_content
```

`~/.omp/profiles/glicc/agent/config.yml`:

```yaml
modelRoles:
  default: glicc/qwen3.8-moe
defaultThinkingLevel: auto
```

```bash
export GLICC_API_KEY="gk_..."
glicc
```

## OpenCode

`~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "glicc": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Glicc",
      "options": {
        "baseURL": "https://llm.glicc.id/v1",
        "apiKey": "{env:GLICC_API_KEY}"
      },
      "models": {
        "qwen3.8-moe": {
          "name": "Qwen3.8 MoE 256K",
          "limit": { "context": 256000, "output": 8192 },
          "reasoning": true,
          "tool_call": true,
          "attachment": true
        }
      }
    }
  }
}
```

```bash
export GLICC_API_KEY="gk_..."
opencode
```

## Other clients

Use the same base URL, key, and model in:

- Continue
- Cline
- Roo Code
- Kilo Code
- Aider
- LiteLLM
- LangChain
- LlamaIndex
- Open WebUI

Claude Code expects the Anthropic Messages API. It needs an OpenAI→Anthropic bridge such as LiteLLM; it cannot use this endpoint directly.

## Runtime behaviour

- One generation slot; extra requests queue.
- A 250K request consumes the context window for the duration.
- `temperature: 0.6`, `top_p: 0.95`, `top_k: 20` is the tuned profile.
- Reasoning is returned in `reasoning_content`.
- MTP drafts two tokens and the target verifies them.
