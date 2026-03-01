# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).



## [1.1-revised] - 2026-03-01

### Added

- `aggregation` field on window objects, constrained to enum: `instant`, `windowed`, `cumulative`
- `inference_mode` field on axis readings, constrained to enum: `deterministic`, `probabilistic`, `composite`
- `model_id` field on axis readings for per-reading model identification
- `space` field on embedding objects
- Typed `provenance` sub-schema inside `meta` with `source_ids`, `sources`, `baseline_status`, `inference_mode`, `providers`, `equation_id`, `merge_rule_id`, `engine`, `engine_version`
- `source_ids`/`sources` pair-integrity `allOf` constraint within `meta.provenance`

### Changed

- Window time fields renamed: `start`/`end` -> `start_utc`/`end_utc`
- Axis reading fields renamed: `axis` -> `name`, `score` -> `value`, `window_id` -> `window_ids` (now an array)
- Axes domain flattened from `{ "readings": [...] }` wrapper to plain array
- Embedding fields renamed: `window_id` -> `window_ids` (now an array), `dimension` -> `dims`
- Embedding `vector` is now required; `confidence` removed
- Privacy only requires `contains_pii` (was also requiring `raw_biosignals_allowed`, `derived_metrics_allowed`)
- Source tracking (`source_ids`, `sources`, `source` def) moved from top-level into `meta.provenance`
- `evidence_source_ids` on axis readings now references `meta.provenance.source_ids` (was top-level `source_ids`)
- Strict validator checks provenance-based source integrity

### Removed

- Top-level `source_ids`/`sources` properties (moved to `meta.provenance`)
- Top-level `allOf` pair-integrity constraint (moved into `$defs/provenance`)
- `axis_name` definition (axis names are now plain strings)
- `unit`, `notes` fields from axis readings
- `embedding_allowed`, `notes` from privacy

## [1.1] - 2026-02-21

### Added

- Context axis domain (`axes.context.readings[]`) for numeric runtime-condition qualifiers (RFC-HSI-0006)
- Provenance guidance: producers place inference/baseline provenance in `meta.provenance` (RFC-HSI-0006)
- `meta` field now permits nested objects and arrays (required for provenance)
- New valid example: `examples/valid/context_with_provenance.json`

### Changed

- Renamed axes domain `affect` to `physiological` for semantic neutrality and wearable data inclusivity
- Renamed example file: `affect_only.json` -> `physiological_only.json`
- Schema file: `schema/hsi-1.1.schema.json` (replaces `hsi-1.0.schema.json` as canonical)
- All examples and test vectors updated to `hsi_version: "1.1"`
- RFC-HSI-0006 status changed from Draft to Accepted

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
