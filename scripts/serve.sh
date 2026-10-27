#!/usr/bin/env bash
set -euo pipefail

mode="${1:-chat}"
root="/root/Desktop/selfhostllm"
cd "$root"

case "$mode" in
  chat)
    spec=(--spec-type draft-mtp --spec-draft-n-max 3 -ctk q4_0 -ctv q4_0 -ub 256)
    ;;
  document)
    spec=(--spec-type draft-mtp --spec-draft-n-max 8 -ctk q4_0 -ctv q4_0 -ub 256)
    ;;
  *)
    echo "usage: $0 [chat|document]" >&2
    exit 2
    ;;
esac

: "${LLAMA_API_KEY:?set LLAMA_API_KEY before starting the server}"
pkill -9 llama-server 2>/dev/null || true

exec engines/llamacpp/build/bin/llama-server \
  -m models/gguf/qwen36-35b-heretic/heretic-Q3_K_M.gguf \
  --mmproj models/gguf/qwen36-35b-heretic/mmproj-BF16.gguf \
  "${spec[@]}" \
  -ngl 99 --split-mode layer -fa on \
  -c 65536 --parallel 1 --cache-reuse 256 \
  --no-mmproj-offload --jinja \
  --temp 1.0 --top-p 0.95 --top-k 20 \
  --api-key "$LLAMA_API_KEY" \
  -a heretic-qwen36-35b \
  --host "${HOST:-127.0.0.1}" --port "${PORT:-8081}"
