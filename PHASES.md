# Native phase timings

Measured with MTP3, Q4 target KV, `ub256`, and the `0004-native-phase-timings.patch` instrumentation. Three runs per workload. Values are median cumulative generation-phase milliseconds per request; prefill-only batches are excluded.

| Workload | Draft | Target verification | MTP catch-up | Sampling/acceptance | Total measured |
|---|---:|---:|---:|---:|---:|
| Chat | 225.9 ms | 780.0 ms | 42.2 ms | 115.0 ms | 1,163.1 ms |
| Document | 413.8 ms | 1,437.1 ms | 78.3 ms | 221.2 ms | 2,150.4 ms |

## Share of measured phase time

| Workload | Draft | Target verification | MTP catch-up | Sampling/acceptance |
|---|---:|---:|---:|---:|
| Chat | 19.4% | **67.1%** | **3.6%** | 9.9% |
| Document | 19.2% | **66.8%** | **3.6%** | 10.3% |

The same runs measured 106.4 chat and 117.7 document decode tok/s, with 71.7% and 84.3% draft acceptance.

## Conclusion

The earlier hypothesis that MTP catch-up was the main avoidable bottleneck is **wrong for this configuration**. Catch-up is only about 3.6% of measured phase time. Target verification dominates at about two-thirds, followed by draft generation at about one-fifth. Optimizing rejected-token catch-up alone therefore cannot produce a large speedup.

The next native candidates must target either target verification cost or the number/cost of draft passes. Instrumentation overhead was not isolated; the phase sums account for most generation time, so they are useful for relative attribution rather than a claim of zero uncovered work.

## Response fields

An instrumented server adds these fields to speculative completion timings:

- `draft_ms`
- `target_ms`
- `catchup_ms`
- `accept_ms`

The benchmark CLI prints them automatically and retains them in raw JSON. Older result files without these fields remain compatible.
