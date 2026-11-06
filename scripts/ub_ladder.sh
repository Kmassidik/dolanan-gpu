#!/usr/bin/env bash
# R33: micro-batch ladder at 256k ctx. Loads each UB, runs the same 53.7k-token
# prefill, records tok/s, keeps the last one that loads. Detached-friendly.
set -u
cd /root/Desktop/selfhostllm
OUT=rnd/r33/ub_ladder.log
: > "$OUT"
BEST=""
for UB in 64 128 256; do
  echo "=== UB=$UB ===" >> "$OUT"
  fuser -k 8084/tcp 2>/dev/null
  for i in $(seq 1 30); do fuser 8084/tcp >/dev/null 2>&1 || break; sleep 1; done
  sleep 2
  UB=$UB setsid nohup /root/Desktop/gpu-optimized/run-llama.sh </dev/null > "logs/ub_$UB.log" 2>&1 &
  OK=0
  for i in $(seq 1 150); do
    sleep 2
    if curl -s -m3 http://127.0.0.1:8084/health | grep -q ok; then OK=1; break; fi
    pgrep -f "llama-server.*8084" >/dev/null || break
  done
  if [ "$OK" != 1 ]; then
    echo "UB=$UB FAILED to load" >> "$OUT"
    grep -iE "error|out of memory|abort|failed" "logs/ub_$UB.log" | tail -3 >> "$OUT"
    continue
  fi
  nvidia-smi --query-gpu=index,memory.used --format=csv,noheader | tr "\n" " " >> "$OUT"; echo >> "$OUT"
  T=$(cat glicc-api.token)
  curl -sS -m 900 -o "/tmp/ub_$UB.out" http://127.0.0.1:8084/v1/chat/completions \
    -H "Authorization: Bearer $T" -H "Content-Type: application/json" --data-binary @/tmp/long60k.json
  .venv/bin/python - "$UB" >> "$OUT" <<'PY'
import json, sys
d = json.load(open(f"/tmp/ub_{sys.argv[1]}.out")); t = d["timings"]
print("prefill %.0f tok/s over %d tokens | decode %.1f tok/s" %
      (t["prompt_per_second"], t["prompt_n"], t["predicted_per_second"]))
PY
  BEST="$UB"
done
echo "=== best working UB: ${BEST:-none} ===" >> "$OUT"
if [ -n "$BEST" ]; then
  fuser -k 8084/tcp 2>/dev/null; sleep 3
  UB=$BEST setsid nohup /root/Desktop/gpu-optimized/run-llama.sh </dev/null > logs/llama_final.log 2>&1 &
  for i in $(seq 1 150); do sleep 2; curl -s -m3 http://127.0.0.1:8084/health | grep -q ok && break; done
  echo "left running on UB=$BEST" >> "$OUT"
fi
