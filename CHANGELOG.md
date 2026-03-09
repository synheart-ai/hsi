# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).



## [1.1] - 2026-03-01

### Added

- `aggregation` field on window objects, constrained to enum: `instant`, `windowed`, `cumulative`
- `inference_mode` field on axis readings, constrained to enum: `deterministic`, `probabilistic`, `composite`
- `model_id` field on axis readings for per-reading model identification
- `space` field on embedding objects
- Typed `provenance` sub-schema inside `meta` with `sources` (ID-keyed map), `baseline_status`, `providers`, `equation_id`, `merge_rule_id`, `engine`, `engine_version`
- `$defs/consent` object with `level` (enum), `embedding`, `raw_biosignals`, `derived_metrics` (booleans)
- Context axis domain (`axes.context.readings[]`) for numeric runtime-condition qualifiers (RFC-HSI-0006)
- Provenance guidance: producers place inference/baseline provenance in `meta.provenance` (RFC-HSI-0006)
- `meta` field now permits nested objects and arrays (required for provenance)
- New valid example: `examples/valid/context_with_provenance.json`

### Changed

- Window time fields renamed: `start`/`end` -> `start_utc`/`end_utc`
- Axis reading fields renamed: `axis` -> `name`, `score` -> `value`, `window_id` -> `window_ids` (now an array)
- Axes domain flattened from `{ "readings": [...] }` wrapper to plain array
- Embedding fields renamed: `window_id` -> `window_ids` (now an array), `dimension` -> `dims`
- Embedding `vector` is now required; `confidence` removed
- Privacy only requires `contains_pii` (was also requiring `raw_biosignals_allowed`, `derived_metrics_allowed`)
- Source tracking (`sources` map, `source` def) moved from top-level into `meta.provenance`; map keys are the authoritative source IDs
- `evidence_source_ids` on axis readings now references keys in `meta.provenance.sources`
- `consent` restructured from enum string to object (`$defs/consent`) with `level`, `embedding`, `raw_biosignals`, `derived_metrics`
- `raw_biosignals_allowed` and `derived_metrics_allowed` moved from privacy into `consent` (renamed to `raw_biosignals` / `derived_metrics`)
- Strict validator builds window/source ID sets directly from map keys
- Renamed axes domain `affect` to `physiological` for semantic neutrality and wearable data inclusivity
- Renamed example file: `affect_only.json` -> `physiological_only.json`
- Schema file: `schema/hsi-1.1.schema.json` (replaces `hsi-1.0.schema.json` as canonical)
- All examples and test vectors updated to `hsi_version: "1.1"`
- RFC-HSI-0006 status changed from Draft to Accepted

### Removed

- Top-level `window_ids` array (windows map keys are the authoritative ID set)
- Top-level `source_ids`/`sources` properties (moved to `meta.provenance`)
- `source_ids` from provenance (sources map keys are the authoritative ID set)
- `allOf` pair-integrity constraints (both top-level and provenance)
- `inference_mode` from provenance (handled per axis_reading)
- `axis_name` definition (axis names are now plain strings)
- `unit`, `notes` fields from axis readings
- `embedding_allowed`, `notes` from privacy
- `raw_biosignals_allowed`, `derived_metrics_allowed` from privacy (moved into consent object)

## [1.0] - 2026-01-01

### Added

- Initial release of the HSI (Human State Interface) canonical contract specification
- JSON schema for HSI payloads: behavior_windows, behavior_readings, emotion_readings, focus_readings, wear_readings
- Axes specification: focus, distraction, emotion (amused, calm, stressed), wear (hr, hrv_rmssd, hrv_sdnn)
- Null-reading conventions for missing or low-confidence data
- Embedding support specification for downstream ML consumers
- RFC-0005: HSI Canonical Contract specification
- HSI Contract Whitepaper (docs/hsi-contract-whitepaper.pdf)
- Validation test suite (Python pytest): valid and invalid example payloads
- CI workflow for schema validation (Python 3.11, 3.12)
- SECURITY.md with HSI-specific privacy and integrity considerations