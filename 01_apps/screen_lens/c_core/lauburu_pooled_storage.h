#ifndef LAUBURU_POOLED_STORAGE_H
#define LAUBURU_POOLED_STORAGE_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MAX_STORAGE_NODES 8
#define VIRTUAL_RING_SLOTS 128
#define DEFAULT_CHUNK_SIZE 65536 // 64 KB

typedef struct {
    char node_id[32];
    char network_role[64];
    uint64_t available_capacity_bytes;
    bool is_active;
} StorageNode;

typedef struct {
    uint32_t chunk_index;
    uint32_t hash_token;
    char assigned_node_id[32];
    uint32_t data_length;
    uint32_t fletcher32_checksum;
} StorageChunkMeta;

typedef struct {
    size_t total_payload_bytes;
    size_t chunk_count;
    size_t active_nodes_count;
    double slice_and_disperse_latency_us;
    double reassemble_latency_us;
    bool bitrot_free;
    bool e2e_sha256_match;
} StoragePoolReport;

/**
 * Initializes consistent hash ring with physical mesh nodes.
 */
void storage_pool_init_ring(void);

/**
 * Adds physical node with virtual ring tokens.
 */
bool storage_pool_add_node(const char *node_id, const char *role, uint64_t capacity_bytes);

/**
 * Slices raw data into chunks, assigns across ring, and computes Fletcher32 checksums.
 */
StoragePoolReport storage_pool_disperse_payload(
    const uint8_t *payload,
    size_t payload_len,
    StorageChunkMeta *out_metas,
    size_t max_chunks,
    uint8_t **out_chunks
);

/**
 * Reassembles chunks into contiguous buffer and verifies bit-for-bit integrity.
 */
bool storage_pool_reassemble_payload(
    const StorageChunkMeta *metas,
    uint8_t **chunks,
    size_t chunk_count,
    uint8_t *out_buffer,
    size_t expected_len
);

/**
 * Sorts the virtual ring slots by token value via qsort.
 */
void storage_pool_sort_ring(void);

/**
 * Computes Fletcher32 checksum with memory alignment safety and odd-byte padding.
 */
uint32_t compute_fletcher32(const uint8_t *data, size_t len);

/**
 * Finds node index on consistent hash ring for given hash using clockwise binary search.
 */
int storage_pool_find_node(uint32_t chunk_hash);

/**
 * Returns physical storage node at index.
 */
const StorageNode *storage_pool_get_node(size_t index);

/**
 * Returns number of registered physical storage nodes.
 */
size_t storage_pool_get_node_count(void);

/**
 * Returns number of virtual ring slots.
 */
size_t storage_pool_get_ring_size(void);

#ifdef __cplusplus
}
#endif

#endif // LAUBURU_POOLED_STORAGE_H
