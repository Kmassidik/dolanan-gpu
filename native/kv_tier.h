#pragma once

#include <cstdint>
#include <cstdlib>

// Select full-attention KV layers to keep in host RAM.
// Example: LLAMA_KV_CPU_LAYERS=3,7,11
inline bool kv_tier_layer_on_cpu(uint32_t layer) {
    const char * value = std::getenv("LLAMA_KV_CPU_LAYERS");
    if (value == nullptr) {
        return false;
    }

    const char * cursor = value;
    while (*cursor != '\0') {
        char * end = nullptr;
        const unsigned long parsed = std::strtoul(cursor, &end, 10);
        if (end != cursor && parsed == layer) {
            return true;
        }
        if (end == cursor) {
            ++cursor;
        } else {
            cursor = end;
        }
        if (*cursor == ',') {
            ++cursor;
        }
    }
    return false;
}
