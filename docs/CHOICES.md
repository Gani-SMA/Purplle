# Architectural Tradeoffs & Decisions — CHOICES.md

This document details three major engineering decisions made during the planning of the Purplle Store Intelligence System, evaluating options considered, AI suggestions, and final design rationales.

---

## 1. Detection Model Selection: YOLOv8x vs. RT-DETR vs. YOLOv9

*   **Context**: The computer vision pipeline requires a model capable of detecting persons (class 0) under challenging shop layouts, with variable lighting, high crowd density, and diverse camera angles.

### Options Considered
1.  **YOLOv8x (Ultralytics)**: Anchor-free detector offering high detection accuracy, extensively optimized for various runtimes.
2.  **RT-DETR (Real-Time DEtection TRansformer)**: End-to-end transformer model. Superior processing speed and higher accuracy in complex scenes but demanding higher GPU memory.
3.  **YOLOv9**: State-of-the-art detector featuring Programmable Gradient Information (PGI). Highly accurate but has less community testing on edge runtimes.

### Evaluation & Suggestions
*   **AI Suggestion**: Deploy **YOLOv8x** due to the abundance of pre-trained weights, mature execution runtimes, and wide compatibility with edge acceleration engines.
*   **Final Choice & Rationale**: **YOLOv8x**. It strikes the best balance between latency and accuracy. Its native integration with PyTorch and standard exports (ONNX, TensorRT) ensures the system remains scalable across both CPU-only servers and GPU-accelerated edge appliances.

---

## 2. Event Schema Strategy: Flat Fields vs. Nested Metadata

*   **Context**: The incoming event payload includes standard fields (timestamps, store IDs, visitor IDs) alongside variable metrics (queue depth, sku zone). We need to determine how to represent these attributes in the database and API.

### Options Considered
1.  **Flat Fields**: Map every potential attribute to its own column in PostgreSQL and field in Pydantic.
2.  **JSONB Nested Metadata**: Keep core telemetry parameters in dedicated columns, storing all auxiliary metadata in a generic nested JSONB block.

### Evaluation & Suggestions
*   **AI Suggestion**: Implement a hybrid approach: store core fields in dedicated columns for indexing, and group optional, variable parameters inside a structured JSONB `metadata` column.
*   **Final Choice & Rationale**: **JSONB Nested Metadata**. This strategy prevents database schema bloat when adding layout-specific telemetry features, while preserving indexing capabilities on keys like `session_seq` or `sku_zone` using GIN indexes.

---

## 3. Session Aggregation: Computed On-Ingest vs. Materialized Views

*   **Context**: Metrics like funnel dropoff and conversions require visitor sessions. We must decide whether to build session states on-the-fly during ingest or calculate them periodically using materialized views.

### Options Considered
1.  **Computed On-Ingest**: Detect ENTRY/EXIT events during ingest and write/update session records synchronously.
2.  **Materialized Views**: Run a cron job to rebuild sessions in batches every hour.

### Evaluation & Suggestions
*   **AI Suggestion**: Perform **On-Ingest Computations** backed by a Redis-based cache mapping to manage state.
*   **Final Choice & Rationale**: **Computed On-Ingest**. Real-time business alerts (such as dead zones or queue spikes) require immediate transactional visibility. Calculating session structures during ingestion guarantees that API responses are always fresh and fully consistent.
