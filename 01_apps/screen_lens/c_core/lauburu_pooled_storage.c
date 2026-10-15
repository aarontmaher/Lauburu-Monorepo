#include "lauburu_pooled_storage.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <time.h>

typedef struct {
    uint32_t token;
    int node_index;
} VirtualRingSlot;

static StorageNode g_nodes[MAX_STORAGE_NODES];
static size_t g_node_count = 0;
static VirtualRingSlot g_ring[VIRTUAL_RING_SLOTS];
static size_t g_ring_size = 0;
static bool g_ring_sorted = false;

// FNV-1a 32-bit hash algorithm
static uint32_t fnv1a_hash(const void *data, size_t len) {
    const uint8_t *bytes = (const uint8_t *)data;
    uint32_t hash = 2166136261u;
    for (size_t i = 0; i < len; ++i) {
        hash ^= bytes[i];
        hash *= 16777619u;
    }
    return hash;
}

// Comparison function for sorting virtual ring slots by token
static int compare_virtual_slots(const void *a, const void *b) {
    const VirtualRingSlot *slot_a = (const VirtualRingSlot *)a;
    const VirtualRingSlot *slot_b = (const VirtualRingSlot *)b;
    if (slot_a->token < slot_b->token) return -1;
    if (slot_a->token > slot_b->token) return 1;
    return 0;
}

void storage_pool_sort_ring(void) {
    if (g_ring_size > 1) {
        qsort(g_ring, g_ring_size, sizeof(VirtualRingSlot), compare_virtual_slots);
    }
    g_ring_sorted = true;
}

// Fletcher32 checksum for zero-overhead bitrot detection with memory alignment safety and odd-byte padding
uint32_t compute_fletcher32(const uint8_t *data, size_t len) {
    if (!data || len == 0) {
        return 0;
    }

    uint32_t sum1 = 0xffff, sum2 = 0xffff;
    size_t words16 = len / 2;
    size_t offset = 0;

    while (words16 > 0) {
        size_t tlen = words16 > 359 ? 359 : words16;
        words16 -= tlen;
        do {
            // Little-endian word extraction: alignment-safe & strict-aliasing compliant
            uint16_t w = (uint16_t)data[offset] | ((uint16_t)data[offset + 1] << 8);
            offset += 2;
            sum1 += w;
            sum2 += sum1;
        } while (--tlen);
        sum1 = (sum1 & 0xffff) + (sum1 >> 16);
        sum2 = (sum2 & 0xffff) + (sum2 >> 16);
    }

    // Handle odd trailing byte with zero high-byte padding
    if (len & 1) {
        uint16_t w = (uint16_t)data[offset];
        sum1 += w;
        sum2 += sum1;
        sum1 = (sum1 & 0xffff) + (sum1 >> 16);
        sum2 = (sum2 & 0xffff) + (sum2 >> 16);
    }

    sum1 = (sum1 & 0xffff) + (sum1 >> 16);
    sum2 = (sum2 & 0xffff) + (sum2 >> 16);
    return (sum2 << 16) | sum1;
}

void storage_pool_init_ring(void) {
    g_node_count = 0;
    g_ring_size = 0;
    g_ring_sorted = false;
    memset(g_nodes, 0, sizeof(g_nodes));
    memset(g_ring, 0, sizeof(g_ring));
}

bool storage_pool_add_node(const char *node_id, const char *role, uint64_t capacity_bytes) {
    if (g_node_count >= MAX_STORAGE_NODES) {
        return false;
    }

    int idx = (int)g_node_count;
    strncpy(g_nodes[idx].node_id, node_id, sizeof(g_nodes[idx].node_id) - 1);
    g_nodes[idx].node_id[sizeof(g_nodes[idx].node_id) - 1] = '\0';
    strncpy(g_nodes[idx].network_role, role, sizeof(g_nodes[idx].network_role) - 1);
    g_nodes[idx].network_role[sizeof(g_nodes[idx].network_role) - 1] = '\0';
    g_nodes[idx].available_capacity_bytes = capacity_bytes;
    g_nodes[idx].is_active = true;
    g_node_count++;

    // Add virtual ring slots per physical node (16 slots per node)
    size_t vslots_per_node = VIRTUAL_RING_SLOTS / MAX_STORAGE_NODES;
    for (size_t v = 0; v < vslots_per_node && g_ring_size < VIRTUAL_RING_SLOTS; ++v) {
        char vkey[64];
        snprintf(vkey, sizeof(vkey), "%s#vslot%zu", node_id, v);
        uint32_t token = fnv1a_hash(vkey, strlen(vkey));

        g_ring[g_ring_size].token = token;
        g_ring[g_ring_size].node_index = idx;
        g_ring_size++;
    }

    g_ring_sorted = false;
    storage_pool_sort_ring();
    return true;
}

// Clockwise binary search / circular successor routing
static int find_node_on_ring(uint32_t chunk_hash) {
    if (g_ring_size == 0) return 0;
    if (!g_ring_sorted) {
        storage_pool_sort_ring();
    }

    // Binary search for first slot with token >= chunk_hash
    size_t low = 0;
    size_t high = g_ring_size;
    while (low < high) {
        size_t mid = low + (high - low) / 2;
        if (g_ring[mid].token >= chunk_hash) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }

    // Circular successor wrap-around: if chunk_hash exceeds all ring tokens, route to g_ring[0]
    if (low < g_ring_size) {
        return g_ring[low].node_index;
    } else {
        return g_ring[0].node_index;
    }
}

int storage_pool_find_node(uint32_t chunk_hash) {
    return find_node_on_ring(chunk_hash);
}

const StorageNode *storage_pool_get_node(size_t index) {
    if (index >= g_node_count) {
        return NULL;
    }
    return &g_nodes[index];
}

size_t storage_pool_get_node_count(void) {
    return g_node_count;
}

size_t storage_pool_get_ring_size(void) {
    return g_ring_size;
}

StoragePoolReport storage_pool_disperse_payload(
    const uint8_t *payload,
    size_t payload_len,
    StorageChunkMeta *out_metas,
    size_t max_chunks,
    uint8_t **out_chunks
) {
    StoragePoolReport rep;
    memset(&rep, 0, sizeof(StoragePoolReport));
    rep.total_payload_bytes = payload_len;
    rep.active_nodes_count = g_node_count;
    rep.bitrot_free = true;

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    size_t chunk_size = DEFAULT_CHUNK_SIZE;
    size_t num_chunks = (payload_len + chunk_size - 1) / chunk_size;
    if (num_chunks > max_chunks) {
        num_chunks = max_chunks;
    }
    rep.chunk_count = num_chunks;

    for (size_t i = 0; i < num_chunks; ++i) {
        size_t offset = i * chunk_size;
        size_t len = (offset + chunk_size <= payload_len) ? chunk_size : (payload_len - offset);

        uint32_t token = fnv1a_hash(payload + offset, len);
        int node_idx = find_node_on_ring(token);

        out_metas[i].chunk_index = (uint32_t)i;
        out_metas[i].hash_token = token;
        out_metas[i].data_length = (uint32_t)len;
        strncpy(out_metas[i].assigned_node_id, g_nodes[node_idx].node_id, sizeof(out_metas[i].assigned_node_id) - 1);
        out_metas[i].assigned_node_id[sizeof(out_metas[i].assigned_node_id) - 1] = '\0';
        out_metas[i].fletcher32_checksum = compute_fletcher32(payload + offset, len);

        out_chunks[i] = (uint8_t *)malloc(len);
        if (out_chunks[i]) {
            memcpy(out_chunks[i], payload + offset, len);
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &t1);
    rep.slice_and_disperse_latency_us = (t1.tv_sec - t0.tv_sec) * 1e6 + (t1.tv_nsec - t0.tv_nsec) / 1e3;
    return rep;
}

bool storage_pool_reassemble_payload(
    const StorageChunkMeta *metas,
    uint8_t **chunks,
    size_t chunk_count,
    uint8_t *out_buffer,
    size_t expected_len
) {
    if (!metas || !chunks || !out_buffer || chunk_count == 0) {
        return false;
    }

    size_t total_reconstructed = 0;
    for (size_t i = 0; i < chunk_count; ++i) {
        if (!chunks[i]) {
            return false;
        }

        uint32_t chk = compute_fletcher32(chunks[i], metas[i].data_length);
        if (chk != metas[i].fletcher32_checksum) {
            return false; // Bitrot detected!
        }

        size_t chunk_offset = (size_t)metas[i].chunk_index * DEFAULT_CHUNK_SIZE;
        if (chunk_offset + metas[i].data_length <= expected_len) {
            memcpy(out_buffer + chunk_offset, chunks[i], metas[i].data_length);
            total_reconstructed += metas[i].data_length;
        } else {
            return false;
        }
    }
    return (total_reconstructed == expected_len);
}
