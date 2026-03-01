# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).



## [1.1-revised] - 2026-03-01

### Added

- `affect` axis domain (`axes.affect[]`) alongside existing physiological, engagement, behavior, context
- `aggregation` field on window objects
- `inference_mode` and `model_id` fields on axis readings
- `space` field on embedding objects

### Changed

- Window time fields renamed: `start`/`end` -> `start_utc`/`end_utc`
- Axis reading fields renamed: `axis` -> `name`, `score` -> `value`, `window_id` -> `window_ids` (now an array)
- Axes domain flattened from `{ "readings": [...] }` wrapper to plain array
- Embedding fields renamed: `window_id` -> `window_ids` (now an array), `dimension` -> `dims`
- Embedding `vector` is now required; `confidence` removed
- Privacy only requires `contains_pii` (was also requiring `raw_biosignals_allowed`, `derived_metrics_allowed`)

### Removed

- `source_ids`, `sources`, and the `source` definition (source tracking removed from schema)
- `axis_name` definition (axis names are now plain strings)
- `evidence_source_ids`, `unit`, `notes` fields from axis readings
- `embedding_allowed`, `notes` from privacy
- `allOf` pair-integrity constraint for sources

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
