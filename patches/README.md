# Native patches

## Adaptive MTP depth (experimental; not production)

Files:

- `0001-adaptive-mtp-depth.patch`: starts each request at the configured maximum depth, reduces depth after low acceptance, and increases it after high acceptance.
- `0002-fast-adaptive-fallback.patch`: falls directly to depth 2 after low acceptance instead of descending one step at a time.
- `0003-adaptive-hysteresis.patch`: prevents depth from growing again after reaching depth 2, avoiding oscillation.

Apply all three in order to llama.cpp revision `aa90d0e6389bddf6d68c81761924fe2efec2a545`:

```bash
cd /root/Desktop/selfhostllm/engines/llamacpp
for p in 0001-adaptive-mtp-depth 0002-fast-adaptive-fallback 0003-adaptive-hysteresis; do
  patch -p1 -i "/root/Desktop/gpu-optimized/patches/$p.patch"
done
cmake --build build --target llama-server -j16
```

The final version reached 94.4 chat and 112.6 document tok/s with `ub256`. Static configurations remained better: MTP2/`ub128` reached 99.8 chat, and MTP8/`ub256` reached 146.1 document tok/s. The patches are retained for evaluation history, not applied to the production server.
