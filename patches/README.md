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

The final version reached 94.4 chat and 112.6 document tok/s with `ub256`. Static configurations remained better: MTP3/Q4 reached 106.3 chat and MTP8/Q4 reached 146.1 document tok/s. These patches are retained for evaluation history, not applied to production.

## Native phase timings (measurement)

`0004-native-phase-timings.patch` adds per-request generation-phase timers and response fields for draft, target verification, MTP catch-up, and sampling/acceptance. The 40-line `native/phase_timer.h` helper is included by the patch. Apply it independently of the adaptive patches:

```bash
cd /root/Desktop/selfhostllm/engines/llamacpp
patch -p1 -i /root/Desktop/gpu-optimized/patches/0004-native-phase-timings.patch
cmake --build build --target llama-server -j16
```

See `PHASES.md` for measured results. Target verification dominates; catch-up is only about 3.6% of measured phase time.
