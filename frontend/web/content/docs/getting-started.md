# Getting started

gliccOps is the operations surface for a self-hosted Qwen3.8 mixture-of-experts deployment on three 8 GB GPUs.

## Surfaces

| Surface | URL | Access |
|---|---|---|
| Command center | `https://llminferences.glicc.id/` | Admin login |
| API keys | `https://llminferences.glicc.id/keys` | Admin login |
| Inference API | `https://llm.glicc.id/v1` | API key |
| Docs | `https://llminferences.glicc.id/docs` | Public |

## Model

```text
model:   qwen3.8-moe
context: 262,144 tokens
MTP:     depth 2
slots:   1
```

The model is 35B total with roughly 3B active parameters per token. It is uncensored/abliterated and served with an inline vision projector.

## First steps

1. Sign in to the command center.
2. Open **API keys**.
3. Create a client key and copy it immediately.
4. Put the key in an environment variable — never in a repository.
5. Configure your harness with the OpenAI-compatible base URL.

## Key rule

```text
base URL: https://llm.glicc.id/v1
key:      created in /keys
model:    qwen3.8-moe
```

The llama.cpp backend key is not a public client key. Use the UI-issued key.
