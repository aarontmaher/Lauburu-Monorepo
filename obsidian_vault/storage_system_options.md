# Distributed Storage System Options

To handle the massive datasets required for 24/7 continuous DPO training and AI telemetry across the heterogeneous Lauburu Mesh (Mac, Linux, Android), we need a robust, mesh-native storage system. 

Here are the top options evaluated by the orchestrator:

## 1. SeaweedFS (Highly Recommended)
*   **Architecture:** Master/Volume servers optimized for billions of small files (perfect for `.jsonl` telemetry logs and AI tensor chunks). 
*   **Pros:** Written in Go, incredibly fast, minimal RAM overhead (crucial for keeping under the 75% RAM Governor limit). It seamlessly spans Mac, Linux, and Android (via Termux), and natively bridges object storage (S3) with POSIX filesystem access via `weed mount`.
*   **Cons:** Less widespread enterprise adoption than Ceph, but tailor-made for our AI edge-mesh use case.

## 2. MinIO
*   **Architecture:** High-performance, S3-compatible object storage.
*   **Pros:** The industry standard for local object storage. Incredibly reliable, excellent UI, and deeply integrates with almost all ML/AI SDKs out of the box. 
*   **Cons:** Strictly object storage (no native POSIX file paths without heavy wrappers). It also tends to be heavier on RAM/CPU, which could violate the mesh hardware governors.

## 3. Ceph
*   **Architecture:** Enterprise distributed block, object, and file storage.
*   **Pros:** The absolute gold standard for data redundancy and hyper-scaling. If a node dies, Ceph self-heals perfectly.
*   **Cons:** Grossly overpowered. Setting up Ceph across a dynamic mesh consisting of MacBooks and Android phones would be extremely complex and computationally expensive. 

## 4. Qdrant (Vector DB)
*   **Architecture:** Native Vector Database.
*   **Pros:** Already heavily used in the AI space for RAG (Retrieval-Augmented Generation). Perfect for storing embedded memory.
*   **Cons:** Not meant for general file storage, binary assets, or raw JSONL logs. Must be paired with one of the above.
