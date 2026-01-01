## RFC-0005: HSI Canonical Contract (HSI 1.0)

- **Status**: Accepted
- **HSI Version**: 1.0
- **Last Updated**: 2025-12-28

### 1. Motivation

Teams routinely produce “human state” outputs (e.g., affect, engagement, attention proxies) using different inputs and implementations. Without a shared contract, interoperability breaks: consumers couple to vendor-specific formats, time handling becomes inconsistent, and “confidence” semantics drift.

HSI defines a stable interface so that:

- Producers can emit human-state signals without exposing implementation details.
- Consumers can validate, compare, and combine signals from multiple producers.
- The contract stays stable as SDKs, models, and signal pipelines evolve independently.

### 2. Design goals

HSI MUST be:

- **Language-agnostic**: JSON payload with a normative JSON Schema.
- **Contract-only**: no SDKs, no model code, no device assumptions.
- **Time-explicit**: all readings are scoped to an explicit time window.
- **Confidence-explicit**: every reading carries a normalized confidence.
- **Source-aware**: producers can express degraded/missing sources.
- **Privacy-first**: no PII allowed; embeddings are treated as sensitive.
- **Strictly validated**: consumers can fail hard on invalid payloads.
- **Access-control compatible**: supports explicit representation of degraded or unavailable
  readings due to authorization or consent constraints.

### 3. Non-goals

HSI does NOT specify:

- how to infer states (ML, heuristics, signal processing)
- how to collect sensor signals
- what device is used
- how to store or visualize outputs
- any canonical model names or embeddings methods

### 4. Terminology

- **Producer**: system that emits an HSI payload.
- **Consumer**: system that validates and uses an HSI payload.
- **Window**: a time-bounded interval the reading applies to.
- **Axis reading**: a normalized score and confidence for a named axis.
- **Source**: an input channel used by the producer (sensor, app, annotation, etc.).
- **Embedding**: a numeric vector representing a latent state; treated as sensitive.

Normative keywords **MUST**, **SHOULD**, and **MAY** are interpreted as described in RFC 2119.

### 5. Canonical payload structure

An HSI payload is a single JSON object with:

- `hsi_version` (string): semantic version for the contract.
- `observed_at_utc` (RFC 3339 string): event-time, when the human state was observed (typically aligns with the latest window end).
- `computed_at_utc` (RFC 3339 string): processing-time, when this payload was produced (must be >= observed_at_utc).
- `producer` (object): producer identity (non-PII).
- `window_ids` (array): index of declared window identifiers.
- `windows` (object): window definitions keyed by window id.
- `axes` (object, optional): axis readings, grouped by domain.
- `source_ids` (array, optional): index of declared source identifiers.
- `sources` (object, optional): source metadata keyed by source id.
- `embeddings` (array, optional): embedding vectors scoped to windows.
- `privacy` (object): privacy assertions.
- `meta` (object, optional): additional non-normative metadata.

Consumers MUST reject payloads that fail schema validation for the declared `hsi_version`.

### 6. Windows

HSI uses **named windows** so multiple readings can share a common time scope without repeating timestamps.

- A producer MUST declare `window_ids` and `windows`.
- A window MUST include:
  - `start` (RFC 3339 date-time)
  - `end` (RFC 3339 date-time)
- A producer MUST ensure `end` is not earlier than `start`.
- A consumer SHOULD treat windows as half-open intervals \([start, end)\) unless domain requirements demand inclusive ends.

### 7. Axes

HSI expresses human-state outputs as axis readings.

Each axis reading MUST include:
- `axis` (string): axis name in `lower_snake_case`.
- `score` (number): normalized score in \([0, 1]\).
- `confidence` (number): normalized confidence in \([0, 1]\).
- `window_id` (string): the window identifier the reading applies to.

Optional fields:
- `evidence_source_ids` (array of strings): sources used to compute this reading.
- `direction` (string): interpretation of score monotonicity. Allowed values are:
  - `"higher_is_more"`
  - `"higher_is_less"`
  - `"bidirectional"` (score represents polarity around a neutral midpoint)
- `notes` (string): non-normative clarification (MUST NOT include PII).

When `direction` is `"bidirectional"`, the score is interpreted relative to a semantic
midpoint (typically 0.5), where lower and higher values represent opposing extremes
of the same construct.

Axes with inherently categorical outputs MUST NOT be represented as axis readings.

#### 7.1 Axis domains

HSI 1.0 defines the following top-level domains under `axes`:

- `axes.affect.readings[]`
- `axes.behavior.readings[]`
- `axes.engagement.readings[]`

Each domain groups axis readings by semantic family:

- Affect represents internal emotional or physiological state.
- Behavior represents observable interaction or activity patterns.
- Engagement represents integrative or derived involvement states, often computed from affective and behavioral signals.

Producers MAY omit axes entirely, or MAY provide only a subset of domains.

Domains MUST NOT be nested, and each axis reading MUST belong to exactly one domain.

#### 7.2 Axis naming guidance (non-exhaustive)

Producers SHOULD use stable, descriptive names. Recommended examples include:

- Affect: `valence`, `arousal`, `stress`, `calm`
- Behavior: `interaction_intensity`, `attention`, `task_persistence`
- Engagement: `engagement_level`, `engagement_stability`, `absorption`

Axis names SHOULD avoid cross-domain ambiguity (e.g., using engagement as both a behavioral and engagement axis).

Consumers MUST NOT assume a closed set of axes; unknown axis values MUST be handled as described in versioning.md.

#### 7.3 Missing and Null Readings (Normative)

An axis reading MAY be explicitly present with a `null` value when a producer is unable
to compute the reading due to access control, missing sources, or other constraints.

- A `null` score MUST NOT be interpreted as zero.
- A `null` score MUST be accompanied by an explanatory field in `meta` or domain-specific
  extensions (e.g., access-control reason codes).
- Omitted axes indicate the producer does not emit that axis at all.

Consumers MUST distinguish between:
- **omitted** axes (not produced)
- **present but null** axes (produced but unavailable)

### 8. Sources

Sources describe input channels used (or expected) by the producer. They are **not** device claims and MUST NOT contain PII.

If `sources` is present:

- `source_ids` MUST be present.
- `sources` MUST be an object keyed by source id.
- A source MUST include:
  - `type`: one of `sensor`, `app`, `self_report`, `observer`, `derived`, `other`
  - `quality`: a number in \([0, 1]\)
  - `degraded`: boolean

Axis readings MAY cite `evidence_source_ids`. If present, each entry MUST reference a declared source.

Confidence represents the producer’s certainty in the correctness of an axis reading,
while source quality represents the reliability or fidelity of an input channel.

### 9. Embeddings

Embeddings are optional. If present, each embedding MUST:
- be scoped to a `window_id`
- include:
  - `window_id` (string): the window identifier the embedding applies to
  - `dimension` (integer)
  - `confidence` (number) in \([0, 1]\)
  - `encoding` (string): one of `float32`, `float64`, `fp16`, `int8`
  - at least one of:
    - `vector` (array of numbers), and/or
    - `vector_hash` (string)

If `vector` is present, producers MUST ensure `dimension` equals the length of `vector`.

If `vector_hash` is present, it MUST be a stable identifier for the embedding contents, and consumers MUST NOT assume the underlying vector is available in the payload.

Embeddings MAY leak sensitive information; see `SECURITY.md`.

NOTE: Access to embeddings may be restricted by producer policy or access-control mechanisms external to HSI. Consumers MUST NOT assume embeddings are always present.

### 10. Privacy

HSI is privacy-first. The payload MUST include:

- `privacy.contains_pii`: MUST be `false`.
- `privacy.raw_biosignals_allowed` (boolean): whether raw biosignal samples are included/allowed.
- `privacy.derived_metrics_allowed` (boolean): whether derived, non-PII metrics are included/allowed.

Optional fields MAY include:

- `privacy.embedding_allowed` (boolean): whether embeddings may be included (defaults to `false` in the schema).
- `privacy.consent`: one of `none`, `implicit`, `explicit`.
- `privacy.purposes`: array of purpose strings.
- `privacy.notes`: non-normative clarification (MUST NOT include PII).

If a producer cannot guarantee `privacy.contains_pii=false`, it MUST NOT emit HSI payloads.

HSI payload production and availability MAY be constrained by external access-control policies (e.g., authorization or consent), resulting in explicitly null readings.

### 11. Compliance levels

HSI defines validator compliance levels:

- **HSI-VALIDATE-BASIC**: validates structural and range constraints using the published schema (Draft 2020-12). If the validator does not support `$data`, it MAY not be able to enforce reference integrity.
- **HSI-VALIDATE-STRICT**: validates structural/range constraints AND enforces reference integrity (e.g., `window_id` and `evidence_source_ids` must reference declared ids). The provided schema includes `$data`-based constraints to enable this in validators that support it.

Producers SHOULD target **HSI-VALIDATE-STRICT** compatibility.

### 12. Versioning

Versioning requirements are normative and defined in `versioning.md`. In summary:

- Producers MUST set `hsi_version` to a semantic version.
- Consumers MUST validate against the schema for the major version they support.
- Minor versions add backward-compatible fields/semantics; majors may break.

### 13. Canonical schema

HSI 1.0 canonical schema is `schema/hsi-1.0.schema.json`.


