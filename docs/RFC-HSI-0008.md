# RFC-HSI-0008

## HSI 1.2 Canonical Contract

- **Status**: Accepted
- **HSI Version**: 1.2
- **Supersedes**: RFC-0005 (for HSI 1.2 payloads); RFC-HSI-0007
- **Relates to**: RFC-HSI-0006 (context axis guidance)
- **Canonical schema**: `schema/hsi-1.2.schema.json`

## 1. Purpose

HSI is the canonical transport contract for human-state frames: time-scoped axis readings produced by heterogeneous pipelines (wearables, models, heuristics) and consumed by systems that need comparable, privacy-bounded signals.

This RFC defines the full normative contract for HSI 1.2 and replaces RFC-0005 as the authoritative specification. RFC-0005 remains the historical record for HSI 1.0. RFC-HSI-0007 is superseded and folded into this document. RFC-HSI-0006 (context axis guidance) remains in force for the `axes.context` domain.

Design goals are unchanged from RFC-0005 §2: language-agnostic, contract-only, time-explicit, confidence-explicit, source-aware, privacy-first, strictly validated, access-control-compatible.

## 2. Relation to prior RFCs

- **RFC-0005** is the HSI 1.0 canonical contract. Its field shapes (`axis`, singular `window_id`, top-level `sources`/`source_ids`, `axes.<domain>.readings[]` wrappers, `start`/`end` window timestamps) apply only to 1.0 payloads. See `schema/hsi-1.0.schema.json`.
- **RFC-HSI-0006** defines the `context` axis domain and places inference/baseline provenance in `meta.provenance`. Its `context` rules remain in force for 1.2.
- **RFC-HSI-0007** introduced the optional `axes.emotion` domain and the refined `inference_mode` vocabulary; both are folded into this document.

## 3. Terminology

- **Producer**: system that emits an HSI payload.
- **Consumer**: system that validates and uses an HSI payload.
- **Window**: a time-bounded half-open interval `[start_utc, end_utc)` that a reading or embedding applies to.
- **Axis reading**: a normalized score and confidence for a named axis, scoped to one or more windows.
- **Domain**: a top-level key under `axes` grouping readings by semantic family. HSI 1.2 defines `physiological`, `behavior`, `engagement`, `context`, and (optional) `emotion`.
- **Source**: an input channel used by the producer (sensor, app, annotation, etc.).
- **Provenance**: the producer's declared assembly metadata for a payload (source map, baseline, engine, equation/merge identifiers).
- **Embedding**: a numeric vector representing a latent state scoped to a window; treated as sensitive.

Normative keywords **MUST**, **SHOULD**, **MAY** are interpreted per RFC 2119.

## 4. Canonical payload structure

An HSI 1.2 payload is a single JSON object with:

- `hsi_version` (string): MUST be `"1.2"`.
- `observed_at_utc` (RFC 3339 date-time): event-time (see §11).
- `computed_at_utc` (RFC 3339 date-time): processing-time; MUST be `>= observed_at_utc`.
- `producer` (object): producer identity (non-PII).
- `windows` (object): window definitions keyed by window id; MUST be non-empty.
- `axes` (object, optional): axis readings grouped by domain.
- `embeddings` (array, optional): embedding vectors scoped to windows.
- `privacy` (object): privacy assertions.
- `meta` (object, optional): additional non-normative metadata. `meta.provenance` is the canonical location for source maps and producer-level assembly metadata.

Top-level fields not listed above MUST be rejected; the schema enforces `additionalProperties: false` at the root.

## 5. Windows

HSI uses named windows so multiple readings can share a common time scope without repeating timestamps.

- `windows` is a map keyed by window id. Map keys are the authoritative window-identifier set.
- Each window MUST include `start_utc` and `end_utc` as RFC 3339 date-times.
- Producers MUST ensure `end_utc >= start_utc`.
- Consumers MUST treat windows as **half-open intervals `[start_utc, end_utc)`** unless a domain-specific extension states otherwise.
- Window ids MUST match the pattern `^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$`.

## 6. Axes

Under `axes`, each domain is a plain array of axis readings (1.2 flattens the 1.0/1.1 `readings[]` wrapper).

### 6.1 Axis domains

- `axes.physiological[]` — readings derived from physiological signals.
- `axes.behavior[]` — observable interaction or activity patterns.
- `axes.engagement[]` — integrative involvement states.
- `axes.context[]` — numeric runtime-condition qualifiers (see RFC-HSI-0006).
- `axes.emotion[]` (optional) — per-class emotion readings.

Domains MUST NOT be nested. Adding a new domain requires a schema update and a version bump; the schema's `additionalProperties: false` on the axes object rejects unknown domains.

### 6.2 Axis reading

Every axis reading is an object with the following **required** fields:

- `name` (string): axis name. In 1.0 this field was called `axis`; in 1.1 and 1.2 it is `name`.
- `score` (number in `[0, 1]` or `null`): normalized score. `null` signals the producer cannot compute a reading due to access control, missing sources, or other constraints; consumers MUST NOT interpret `null` as zero. A `null` score requires a non-empty top-level `meta` explanation.
- `confidence` (number in `[0, 1]`).
- `direction` (string): `higher_is_more`, `higher_is_less`, or `bidirectional`. In 1.2 `direction` is **required** (optional in 1.0). `bidirectional` scores are interpreted relative to a semantic midpoint (typically 0.5).
- `inference_mode` (string): see §6.3.
- `model_id` (string): URI-shaped identifier matching `^[a-z][a-z0-9+.-]*://[^\s]+$`. Reserved schemes: `model://` (learned/ensemble artifacts), `rulepack://` (deterministic rule bundles), `provider://` (third-party/platform attributions).
- `window_ids` (array of strings, `uniqueItems: true`): SHOULD reference keys in `/windows`.
- `evidence_source_ids` (array of strings, `uniqueItems: true`): SHOULD reference keys in `meta.provenance.sources`. MAY be empty.

Optional: `notes` (string; MUST NOT include PII).

Axes with inherently categorical outputs MUST NOT be represented as axis readings.

### 6.3 `inference_mode` vocabulary

- `probabilistic_model` — learned or ensemble outputs (e.g. ONNX models).
- `deterministic_rule` — closed-form transforms, rulepacks, or deterministic feature passthroughs.
- `external_provider` — values dominated by a third-party or platform API (e.g. HealthKit sleep).
- `composite` — explicit merge of multiple inference paths.

### 6.4 Emotion head (optional)

`axes.emotion[]` uses the same axis-reading shape as other domains. Each emotion class is expressed as its own reading with `name` set to a `lower_snake_case` label (e.g. `emotion.stress`, `emotion.calm`) and a scalar `score` in `[0, 1]`. Producers that want to advertise a full normalized distribution SHOULD emit one reading per modeled class whose scores sum to `1.0`.

Validators do not enforce sum-to-1.0: partial emission is allowed, and the payload alone does not signal whether a distribution is full or partial. Consumers that require a normalized distribution SHOULD verify the sum themselves or require a producer-level contract.

### 6.5 Axis naming guidance

Producers SHOULD use stable, descriptive, `lower_snake_case` names. Examples:

- Physiological: `valence`, `arousal`, `stress`, `calm`.
- Behavior: `interaction_intensity`, `attention`, `task_persistence`.
- Engagement: `engagement_level`, `engagement_stability`, `absorption`.
- Context: see RFC-HSI-0006 §3.
- Emotion: `emotion.stress`, `emotion.calm`, `emotion.joy`, etc.

Consumers MUST NOT assume a closed set of axis *names*; unknown names within a known domain MUST be tolerated (see `versioning.md`).

### 6.6 Null and missing readings

- Omitted axes indicate the producer does not emit that axis at all.
- `score: null` indicates the producer tried to emit but could not.
- Consumers MUST distinguish **omitted** from **present-but-null**.
- A `null` score MUST be accompanied by a non-empty `meta` explanation (e.g. `meta.null_reading_reason` with an access-control reason code).

## 7. Sources and provenance

HSI 1.2 carries source metadata inside `meta.provenance.sources`. The source-map keys are the authoritative source-identifier set.

- `meta.provenance.sources` is an object keyed by source id, non-empty when present.
- Each source MUST include `type` (one of `sensor`, `app`, `self_report`, `observer`, `derived`, `other`), `quality` (number in `[0, 1]`), and `degraded` (boolean). Optional: `notes`.
- `axis_reading.evidence_source_ids` entries MUST reference declared source ids.

`meta.provenance` MAY also include `baseline_status` (string), `providers` (array of `{id, version}`), `engine` (string), `engine_version` (string), `equation_id` (string), `merge_rule_id` (string), `srm_snapshot_id` (string). Fields not declared in the schema MUST be rejected; `meta.provenance` uses `additionalProperties: false`.

Source **quality** describes the reliability of an input channel. Axis reading **confidence** describes the producer's certainty in the correctness of the reading. They are distinct and not interchangeable.

## 8. Embeddings

Embeddings are optional. Each embedding MUST:

- be scoped to a single `window_id` (string; SHOULD reference a key in `/windows`);
- include `dimension` (integer ≥ 1), `encoding` (one of `float32`, `float64`, `fp16`, `int8`), and `confidence` (number in `[0, 1]`);
- include at least one of `vector` (array of numbers) or `vector_hash` (string).

If both `vector` and `dimension` are present, `dimension` MUST equal `len(vector)`.

`vector_hash`, when present, MUST match `^sha256:[0-9a-f]{64}$`. Producers SHOULD compute the hash over a canonical encoding of the embedding content; **RFC 8785 (JSON Canonicalization Scheme)** is RECOMMENDED for canonicalizing the vector array before hashing. If `vector_hash` is present without `vector`, consumers MUST NOT assume the vector is available in the payload.

Embeddings MAY leak sensitive information (see `SECURITY.md`). Producers SHOULD treat embeddings as sensitive and restrict their distribution.

## 9. Privacy

`privacy` MUST include:

- `contains_pii`: MUST be `false` (enforced as a schema `const`). If a producer cannot guarantee this, it MUST NOT emit HSI.
- `raw_biosignals_allowed` (boolean).
- `derived_metrics_allowed` (boolean).

Optional fields:

- `embedding_allowed` (boolean; defaults to `false`).
- `consent` (string): one of `none`, `implicit`, `explicit`.
- `purposes` (array of strings, `uniqueItems: true`): controlled vocabulary of `research`, `personalization`, `safety_monitoring`, `clinical_support`, `product_telemetry`, `other`. Producers emitting a purpose outside this set MUST use `other` and describe the specific purpose in `privacy.notes`.
- `notes` (string; MUST NOT include PII).

## 10. Compliance levels

- **HSI-VALIDATE-BASIC**: validates structural and range constraints against `schema/hsi-1.2.schema.json` using a Draft 2020-12 validator.
- **HSI-VALIDATE-STRICT**: BASIC plus reference-integrity checks enforced in code (`tests/hsi_validate.py`):
  - `computed_at_utc >= observed_at_utc`;
  - `window.end_utc >= window.start_utc` for each declared window;
  - `axis_reading.window_ids` entries reference declared `/windows` keys;
  - `axis_reading.evidence_source_ids` entries reference declared `meta.provenance.sources` keys (when non-empty);
  - null-score readings require a non-empty top-level `meta`;
  - `embedding.window_id` references a declared window;
  - `embedding.dimension` equals `len(vector)` when `vector` is present.

Producers SHOULD target HSI-VALIDATE-STRICT compatibility.

## 11. Temporal semantics

- `observed_at_utc` is event-time — the moment the human state applies to. Producers emitting a single window SHOULD set `observed_at_utc = window.end_utc`. Producers emitting multiple windows SHOULD set `observed_at_utc = max(windows[*].end_utc)` unless they document an alternative event-time policy in `meta`.
- `computed_at_utc` is processing-time — when the payload was assembled. `computed_at_utc >= observed_at_utc` MUST hold.
- Windows are half-open `[start_utc, end_utc)` (§5).
- All timestamps are RFC 3339 and MUST be in UTC (`Z` suffix or `+00:00`).

## 12. Versioning

Versioning is defined in `versioning.md`. HSI is **pre-stable**: until `2.0`, minor versions MAY introduce breaking contract changes. Producers MUST set `hsi_version` to the contract version they claim; consumers SHOULD validate each payload against the schema matching its declared `hsi_version`.

## 13. Security and privacy

See `SECURITY.md`. Key constraints:

- No PII in any field.
- Embeddings are sensitive even in aggregate and MAY leak health/identity correlates.
- HSI payloads SHOULD be transmitted over authenticated, encrypted channels.
- `producer.instance_id` is a stable correlator; see `SECURITY.md` for rotation guidance.
- Payload integrity and signing are currently out of scope for this contract; consumers that require integrity MUST layer it externally (e.g. JWS over a canonicalized payload).

## 14. Canonical schema

The canonical HSI 1.2 schema is `schema/hsi-1.2.schema.json`.
