# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
HSI uses `MAJOR.MINOR` versioning and is pre-stable — minor versions MAY introduce breaking contract changes until `2.0`. See [`versioning.md`](versioning.md) for the full stability policy.

## [1.3] - 2026-05-02

### Added

- Canonical validation schema `schema/hsi-1.3.schema.json` (RFC-HSI-0010 + RFC-HSI-0011 land together).
- **Five-axis canonical domain set** (RFC-HSI-0010 §4): `axes` is closed via `additionalProperties: false` to `physiological`, `kinematic`, `digital`, `cognitive`, `affective`. The 1.2 domains `behavior`, `engagement`, `context`, and `emotion` are dissolved (mappings in RFC-HSI-0010 §11).
- **Modality attribution by domain key** (RFC-HSI-0010 §5): `axis_reading` gains an optional `modalities_used` array (`uniqueItems`, `minItems: 1`, items drawn from `["physiological", "kinematic", "digital"]`). Required on every reading in `axes.cognitive[]` and `axes.affective[]`; forbidden on readings in the three single-modality domains. Schema enforces the required/forbidden split via `axes_domain_single_modality` / `axes_domain_multimodal`. Strict validator emits `HSI-1.3-MODALITIES-USED-MISSING` and `HSI-1.3-MODALITIES-USED-FORBIDDEN`.
- **Categorical reading shape** (RFC-HSI-0010 §8): `direction` enum extended with `categorical`; new `label` (lowercase token) and `categories` (array, `uniqueItems`, `minItems: 2`). When `direction == "categorical"`, `label` and `categories` are required and `score` MUST be `null`; otherwise `label` and `categories` MUST be absent. Discriminator implemented via `if/then/else`. Strict validator enforces `label ∈ categories` (`HSI-1.3-CATEGORICAL-LABEL-IN-CATEGORIES`).
- **Direction enum rename** (RFC-HSI-0010 §7): `lower_is_more` replaces 1.2's `higher_is_less`. 1.3 schemas reject `higher_is_less`; 1.2 schemas continue to accept it.
- **Per-modality fidelity tiers on sources** (RFC-HSI-0011): new `meta.provenance.sources[*].tiers` object with optional integer keys `physiological` (1–4), `kinematic` (1–3), `digital` (1–3); `additionalProperties: false`, `minProperties: 1`. Replaces the 1.2 `source.source_tier` integer at the only site it lived in 1.2 (post-PR #5). Readings and embeddings derive their effective per-modality tier by resolving `evidence_source_ids` against the source map and taking the most conservative (highest-numbered) value across cited sources for each modality (RFC-HSI-0011 §6.3). Source-only placement; `tiers` is rejected on `axis_reading` and `embedding` via existing `additionalProperties: false`.
- **Strict validator** path `tests/hsi_validate.py::_validate_strict_13` and dispatcher entry for `hsi_version: "1.3"`. Enforces the 1.2 STRICT carryovers (windows, evidence-source integrity on readings and embeddings, observed/computed ordering, dimension/vector consistency, null-score meta), the 1.3 axis-domain set, the modalities_used split, the categorical-label rule, and the 1.3 source-only tiers (rejects 1.2 `source_tier` on sources).
- New valid examples: `examples/valid/runtime_snapshot_1_3.json` (full 5-axis with categorical kinematic and multimodal cognitive/affective), `examples/valid/multimodal_cognitive.json`, `examples/valid/categorical_kinematic.json`, `examples/valid/digital_only.json`, `examples/valid/tiers_multimodal.json`, `examples/valid/tiers_digital_only.json`.
- New invalid examples: `examples/invalid/missing_modality.json` (modalities_used on a single-modality domain reading), `examples/invalid/multimodal_without_modalities_used.json`, `examples/invalid/affective_from_digital_only.json`, `examples/invalid/categorical_score_conflict.json`, `examples/invalid/tiers_source_tier_present.json`, `examples/invalid/tiers_on_axis_reading.json`, `examples/invalid/tiers_empty_object.json`, `examples/invalid/tiers_unknown_modality.json`.
- 1.3 regression fixture under `test-vectors/v1.3/`.

### Changed

- **Breaking (contract)**: `axes` properties redefined as the closed 5-domain set above; 1.2's `engagement`, `behavior`, `context`, `emotion` are no longer recognized at the schema level for 1.3 payloads. Migration guidance in RFC-HSI-0010 §11.
- **Breaking (contract)**: `direction: "higher_is_less"` is removed from the 1.3 enum in favor of `direction: "lower_is_more"`. 1.2 payloads continue to validate against `schema/hsi-1.2.schema.json` with the old name.
- **Breaking (contract)**: `meta.provenance.sources[*].source_tier` (integer) is replaced by `meta.provenance.sources[*].tiers` (per-modality object). 1.3 schemas reject `source_tier` at every historical site (`axis_reading`, `embedding`, source). 1.2 → 1.3 producer rename: `source.source_tier: N` → `source.tiers: { "physiological": N }`. The 1.2 schema is unchanged.

### Removed

- `axes.engagement`, `axes.behavior`, `axes.context`, `axes.emotion` as canonical 1.3 domain keys (RFC-HSI-0010 §11). Members migrate per the §11.2–§11.5 mapping; affective members move out of the prefix convention (`emotion.stress` → `stress`).
- `meta.provenance.sources[*].source_tier` (replaced by `tiers`).
- `$defs/source_tier` definition (no longer referenced after the per-source field is replaced).

## [1.2] - 2026-04-18

### Added

- Canonical validation schema `schema/hsi-1.2.schema.json` as the contract version exercised by examples, test vectors, and CI.
- `axes.emotion` domain (optional) using the same per-reading shape as other domains.
- Per-axis-reading `inference_mode` and `model_id` (required), `window_ids` (array), and `name` (replaces legacy `axis`).
- `source.source_tier` (optional): signal-fidelity tier declared at the source itself in `meta.provenance.sources`. Readings and embeddings derive their effective tier by resolving `evidence_source_ids` against the source map and taking the most conservative (highest-numbered) tier across cited sources. `source_tier` is no longer permitted on individual readings or embeddings (see Removed). Additive at the source level — existing payloads without `source_tier` on sources continue to validate.
- `embedding.evidence_source_ids` (optional): mirrors `axis_reading.evidence_source_ids` so producers can declare which sources backed an embedding. Consumers resolve each id against `meta.provenance.sources` for type / quality / `source_tier`. HSI-VALIDATE-STRICT enforces reference integrity for non-empty arrays. Additive.
- `source.device_class`, `source.signals`, `source.transport`, `source.vendor` (all optional): orthogonal descriptors alongside the existing `type` enum. `type` stays coarse ("role" — sensor / app / self_report / observer / derived / other); `device_class` captures physical form factor ("strap" / "watch" / "ring" / "patch" / …); `signals` is a free-form array of what the source measures (`ppg`, `hrv`, `ecg`, `accel`, …); `transport` captures how data reaches the producer (`ble` / `ant` / `inproc` / …); `vendor` is a non-normative manufacturer tag. Producers can describe an Apple Watch as `{ type: sensor, device_class: watch, signals: ["ppg","hrv","accel"], transport: ble, vendor: apple }` without ambiguity. Additive — existing sources that only set `type` continue to validate.
- Example fixture `examples/valid/runtime_snapshot.json` mirroring the payload emitted by `synheart-state-runtime` (rulepack-driven axes across `physiological` / `engagement` / `emotion`, embedding with `evidence_source_ids`, per-source `source_tier` in provenance, producer-defined `meta.ids` + `meta.snapshot_type`).
- Invalid fixtures `examples/invalid/embedding_unknown_evidence_source.json` and `examples/invalid/source_tier_out_of_range.json` covering the new surface area.
- RFC-HSI-0008 §6.7 / §7 / §8 / §10 updated for the authoritative-source-tier semantics, the full `source` descriptor set, and `embedding.evidence_source_ids` (including its STRICT reference-integrity rule).
- Strict validator (`tests/hsi_validate.py::_validate_strict_12`): `embedding.evidence_source_ids` entries are now checked against `meta.provenance.sources` keys for HSI-VALIDATE-STRICT compliance, matching the existing `axis_reading.evidence_source_ids` rule.

### Privacy considerations (1.2 source descriptors)

- `device_class`, `signals`, and `transport` describe equipment *capabilities* (analogous to a Content-Type header) with modest entropy on their own; they do not compromise `privacy.contains_pii: false`.
- `vendor` is the highest-entropy addition and the one most relevant to fingerprinting. It is not PII per GDPR/HIPAA, but in combination with session identifiers or cross-payload correlation it narrows re-identification (brand choice correlates with income, tech-adoption, and region). Producers SHOULD omit `vendor` in privacy-sensitive contexts — especially when `privacy.purposes` is research-only and payloads may be joined across subjects. Retain it when the consumer genuinely needs vendor-specific signal calibration (e.g., HRV-algorithm differences between Polar and Garmin). The schema enforces no automatic stripping; this is a producer choice.
- Consumers SHOULD tolerate absent descriptors (treat as unknown) rather than rejecting payloads that elect to redact for privacy reasons.

### Changed

- **Breaking (contract)**: Top-level `window_ids` / `source_ids` / `sources` removed in favor of `windows` map keys as the sole window registry and `meta.provenance.sources` for evidence.
- **Breaking (contract)**: Window timestamps renamed to `start_utc` / `end_utc` (replacing `start` / `end`).
- **Breaking (contract)**: Axis domains are arrays of readings under `axes.<domain>` (replacing `axes.<domain>.readings[]`).
- Examples under `examples/valid/`, invalid fixtures under `examples/invalid/`, and `test-vectors/` updated to `hsi_version: "1.2"` and the new shapes.
- Strict validator (`tests/hsi_validate.py`): split into explicit per-version paths `_validate_strict_10` / `_validate_strict_11` / `_validate_strict_12` dispatched by `hsi_version`. Each path enforces the reference-integrity rules specific to that version's field shape (e.g. 1.0 `window_id` singular + top-level sources/source_ids; 1.1 `name`/`value` + `meta.provenance.sources`; 1.2 `score` + refined `inference_mode` vocabulary).
- Pytest suite routes each fixture to the schema matching its declared `hsi_version`; regression fixtures added under `test-vectors/v1.0/` and `test-vectors/v1.1/` to keep the older strict paths exercised in CI.

### Removed

- `axis_reading.source_tier` and `embedding.source_tier`. `source_tier` lives canonically on each entry in `meta.provenance.sources`; consumers derive the effective reading-/embedding-level tier from `evidence_source_ids` (RFC-HSI-0008 §6.7). Producers that need to express a degraded subset of an otherwise higher-fidelity channel SHOULD model it as a separate source entry rather than overriding tier on the reading. Invalid fixtures `examples/invalid/axis_reading_source_tier.json` and `examples/invalid/embedding_source_tier.json` lock in the rejection.

## [1.1] - 2026-03-01

### Added

- `aggregation` field on window objects, constrained to enum: `instant`, `windowed`, `cumulative`
- `inference_mode` field on axis readings, constrained to enum: `deterministic`, `probabilistic`, `composite`
- `model_id` field on axis readings for per-reading model identification
- `space` field on embedding objects
- Typed `provenance` sub-schema inside `meta` with `sources` (ID-keyed map), `baseline_status`, `providers`, `equation_id`, `merge_rule_id`, `engine`, `engine_version`
- `$defs/consent` object with `level` (enum), `embedding`, `raw_biosignals`, `derived_metrics` (booleans)
- Context axis domain (`axes.context[]`) for numeric runtime-condition qualifiers (RFC-HSI-0006)
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