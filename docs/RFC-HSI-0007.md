# RFC-HSI-0007

## HSI 1.2 — Emotion head and inference vocabulary

- **Status**: Draft
- **Type**: Minor version (additive on 1.1)
- **Target**: HSI 1.2
- **Owner**: HSI Maintainers

## 1. Purpose

HSI 1.2 adds optional **`axes.emotion`** and a normative **`inference_mode`** vocabulary for per-reading and provenance metadata, without removing HSI 1.1 payloads.

## 2. Schema

- **`hsi_version`**: MUST be `"1.2"` for payloads claiming this contract.
- **`axes.emotion.readings[]`**: optional domain; each item is an **emotion reading** with `name` equal to `"emotion"`, `value` an object mapping `lower_snake_case` class labels to masses in `[0, 1]`, plus `confidence`, `direction`, `window_ids`, `evidence_source_ids`, `inference_mode`, and `model_id`. Producers SHOULD normalize class masses to sum to `1.0` when they represent a full distribution.
- **Legacy axis readings** (`axes.*.readings[]` except emotion): optional `inference_mode` and `model_id` on the same objects as in HSI 1.1 (`axis`, `score`, `window_id`, …).

## 3. `inference_mode` enum

- **`probabilistic_model`** — learned or ensemble outputs (e.g. ONNX).
- **`deterministic_rule`** — closed-form transforms, rulepacks, or deterministic feature passthrough.
- **`external_provider`** — values dominated by a third-party or platform API (e.g. HealthKit sleep).
- **`composite`** — explicit merge of multiple inference paths.

The same strings MAY appear under `meta.provenance.inference_mode` for coarse producer-level hints.

## 4. Migration

Existing **HSI 1.1** documents remain valid under `hsi-1.1.schema.json`. New producers that emit the emotion head or per-reading inference metadata SHOULD use **1.2** and `hsi-1.2.schema.json`.
