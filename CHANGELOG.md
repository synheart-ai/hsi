# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2] - 2026-04-18

### Added

- Canonical validation schema `schema/hsi-1.2.schema.json` as the contract version exercised by examples, test vectors, and CI.
- `axes.emotion` domain (optional) using the same per-reading shape as other domains.
- Per-axis-reading `inference_mode` and `model_id` (required), `window_ids` (array), and `name` (replaces legacy `axis`).

### Changed

- **Breaking (contract)**: Top-level `window_ids` / `source_ids` / `sources` removed in favor of `windows` map keys as the sole window registry and `meta.provenance.sources` for evidence.
- **Breaking (contract)**: Window timestamps renamed to `start_utc` / `end_utc` (replacing `start` / `end`).
- **Breaking (contract)**: Axis domains are arrays of readings under `axes.<domain>` (replacing `axes.<domain>.readings[]`).
- Examples under `examples/valid/`, invalid fixtures under `examples/invalid/`, and `test-vectors/` updated to `hsi_version: "1.2"` and the new shapes.
- Strict validator (`tests/hsi_validate.py`): HSI 1.2 uses provenance-backed evidence checks, `start_utc`/`end_utc` ordering, and window references via `/windows` keys; HSI 1.0/1.1 payloads still use the legacy strict path when `hsi_version` is not `1.2`.
- Pytest suite validates all fixtures against `hsi-1.2.schema.json` only.

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
