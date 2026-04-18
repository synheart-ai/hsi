# RFC-HSI-0007

## HSI 1.2 — Emotion head and inference vocabulary

- **Status**: Superseded by [RFC-HSI-0008](./RFC-HSI-0008.md)
- **Type**: Minor version (additive on 1.1)
- **Target**: HSI 1.2
- **Owner**: HSI Maintainers

> **Note:** This document introduced the `axes.emotion` domain and the refined `inference_mode` vocabulary for HSI 1.2. Both are now defined normatively by **[RFC-HSI-0008](./RFC-HSI-0008.md)**, the canonical 1.2 contract. The text below is retained as the historical motivation.

## 1. Purpose

HSI 1.2 adds optional **`axes.emotion`** and a normative **`inference_mode`** vocabulary for per-reading and provenance metadata, without removing HSI 1.1 payloads.

## 2. Schema

- **`hsi_version`**: MUST be `"1.2"` for payloads claiming this contract.
- **Axes shape (breaking vs 1.1)**: Every domain under `axes` is an **array of axis readings** (not an object wrapping a `readings[]` array). This applies uniformly to `physiological`, `behavior`, `engagement`, `context`, and `emotion`.
- **Axis reading fields**: Each reading is an object with required `name`, `score` (number in `[0, 1]` or `null`), `confidence`, `direction`, `window_ids`, `evidence_source_ids`, `inference_mode`, and `model_id`. Optional: `notes`. The legacy `axis` field is removed — use `name`.
- **`axes.emotion`**: optional domain using the same `axis_reading` shape as the other domains. Each class is expressed as its **own reading**, with `name` set to a `lower_snake_case` label (e.g. `"emotion.stress"`, `"emotion.calm"`) and a scalar `score` in `[0, 1]`. This keeps emotion composable with the rest of the contract and with tooling that iterates readings uniformly; producers that need a normalized distribution SHOULD emit one reading per class whose scores sum to `1.0`.
- **Sum-to-1.0 is NOT validator-enforced.** Partial emission is allowed (e.g. a producer may emit only `emotion.stress` without the full class set), so validators cannot distinguish a partial from a full distribution from payload shape alone. Producers that want to advertise a full distribution SHOULD emit every class they model in the same payload; consumers that require a normalized distribution SHOULD verify the sum themselves or require a producer-level contract.

## 3. `inference_mode` enum

- **`probabilistic_model`** — learned or ensemble outputs (e.g. ONNX).
- **`deterministic_rule`** — closed-form transforms, rulepacks, or deterministic feature passthrough.
- **`external_provider`** — values dominated by a third-party or platform API (e.g. HealthKit sleep).
- **`composite`** — explicit merge of multiple inference paths.

The same strings MAY appear under `meta.provenance.inference_mode` for coarse producer-level hints.

## 4. Migration

New producers SHOULD emit **HSI 1.2** against `hsi-1.2.schema.json`. Existing **HSI 1.1** payloads remain valid under `hsi-1.1.schema.json`.
