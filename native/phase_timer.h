#pragma once

#include "server-common.h"

#include <cstdint>

// Add elapsed time only to slots whose complete draft belongs to this sub-batch.
template <typename Slots>
void phase_add_verify_time(
        Slots &slots,
        int32_t off,
        int32_t n_tokens,
        uint64_t server_slot_stats::* field,
        int64_t started_us) {
    const uint64_t elapsed_us = ggml_time_us() - started_us;
    for (auto & slot : slots) {
        if (slot.spec_draft.empty() || slot.spec_i_batch.empty()) {
            continue;
        }
        bool complete = true;
        for (const int32_t index : slot.spec_i_batch) {
            complete = complete && index >= off && index < off + n_tokens;
        }
        if (complete) {
            slot.stats.*field += elapsed_us;
        }
    }
}

// Scoped timer remains correct through acceptance rollback's early return.
struct phase_scope {
    uint64_t &total_us;
    const int64_t started_us;

    explicit phase_scope(uint64_t &total_us)
        : total_us(total_us), started_us(ggml_time_us()) {}

    ~phase_scope() {
        total_us += ggml_time_us() - started_us;
    }
};
