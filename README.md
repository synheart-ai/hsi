## Human State Interface (HSI)

[![Version](https://img.shields.io/badge/version-1.3-blue.svg)](schema/hsi-1.3.schema.json)
[![Schema](https://img.shields.io/badge/schema-JSON%20Draft%202020--12-green.svg)](https://json-schema.org/draft/2020-12/schema)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![RFC](https://img.shields.io/badge/RFC--HSI--0008-1.2_canonical-purple.svg)](docs/RFC-HSI-0008.md)
[![RFC](https://img.shields.io/badge/RFC--HSI--0010-1.3_axes_modalities-purple.svg)](docs/RFC-HSI-0010.md)
[![RFC](https://img.shields.io/badge/RFC--HSI--0011-1.3_confidence_breakdown-purple.svg)](docs/RFC-HSI-0011.md)
[![Specification](https://img.shields.io/badge/specification-contract--only-orange.svg)](#what-hsi-is)
[![Whitepaper](https://img.shields.io/badge/whitepaper-read-brightgreen.svg)](docs/hsi-contract-whitepaper.pdf)



HSI is a **foundational interface specification** for representing and exchanging
**human-state signals** across independent systems — similar in role to
APIs, file formats, or coordinate systems (e.g., HTTP, JSON, GPS).

This repository defines the **authoritative HSI contract only**:
the canonical payload structure, field semantics, validation schema,
versioning rules, and reference test vectors.

HSI enables interoperability between producers and consumers of inferred
human state (e.g., physiological signals, focus, engagement, recovery) without requiring
shared models, shared SDKs, or shared infrastructure.


> **Mental model:** HSI is to human-state data what JSON is to structured data
> or GPS is to location — a shared interface that many systems can implement.

 **HSI intentionally defines *what* is exchanged, not *how* it is produced.**

### Why HSI exists

As human-state inference systems proliferate (wearables, on-device models,
behavioral analytics, affective computing), teams increasingly need to
exchange *results* — not raw signals or model internals.

Without a standard interface:

- Producers couple consumers to implementation details
- Time-window semantics drift
- Confidence and uncertainty become ambiguous
- Privacy boundaries are inconsistently enforced

HSI solves this by defining a **stable, implementation-agnostic interface**
for human-state outputs — independent of devices, models, or vendors.

### What HSI is

- A **standardized interface contract** for human-state outputs
- A **canonical JSON representation** with explicit temporal scope
- A **versioned schema** with forward-compatibility guarantees
- A **shared structure** for domains and axis readings (without assuming a closed vocabulary of axis names)


### What HSI is not

- **Not an SDK** or framework
- **Not tied to Synheart** or any single implementation
- Not a model, dataset, or training recipe
- Not a signal acquisition or processing standard

### Roles

- **Producer**: generates an HSI payload from any internal logic (models, heuristics, sensors, annotations) and MUST emit payloads that validate against the referenced schema for the claimed `hsi_version`.
- **Consumer**: validates and interprets an HSI payload. Consumers MUST treat HSI as an interface contract and MUST NOT assume the producer’s implementation details.
>Consumers MUST treat unknown fields as forward-compatible extensions
### Specification entry points

- **Canonical RFCs (HSI 1.3)**:
  - [`docs/RFC-HSI-0010.md`](docs/RFC-HSI-0010.md) — 5-axis canonical domain set (`physiological`, `kinematic`, `digital`, `cognitive`, `affective`), modality attribution, categorical readings.
  - [`docs/RFC-HSI-0011.md`](docs/RFC-HSI-0011.md) — optional `confidence_breakdown` per-channel attribution on multimodal readings.
  - [`docs/RFC-HSI-0009.md`](docs/RFC-HSI-0009.md) — optional payload integrity block (content hash + detached signature).
- **Authoritative RFC (HSI 1.2)**: [`docs/RFC-HSI-0008.md`](docs/RFC-HSI-0008.md) — canonical 1.2 contract; supersedes RFC-0005 and folds in RFC-HSI-0007. 1.2 payloads remain valid against `schema/hsi-1.2.schema.json`.
- **Historical RFC (HSI 1.0)**: [`docs/RFC-0005-hsi-canonical-contract.md`](docs/RFC-0005-hsi-canonical-contract.md)
- **Context axis guidance (1.1 / 1.2)**: [`docs/RFC-HSI-0006.md`](docs/RFC-HSI-0006.md). Note: `axes.context` is dissolved in 1.3; runtime-context info moves to `meta.provenance` (RFC-HSI-0010 §11.5).
- **Validation schema (HSI 1.3, canonical)**: `schema/hsi-1.3.schema.json`
- **Earlier schemas**: `schema/hsi-1.2.schema.json`, `schema/hsi-1.1.schema.json`, `schema/hsi-1.0.schema.json` — retained for historical payloads. Producers and consumers dispatch on `hsi_version` and validate against the schema for the declared version.
- **Versioning policy**: `versioning.md`
- **Security and privacy**: `SECURITY.md`
- **Examples**: `examples/` (1.3 examples include `runtime_snapshot_1_3.json`, `multimodal_cognitive.json`, `categorical_kinematic.json`, `digital_only.json`, `confidence_breakdown.json`, `affective_digital_only_research.json`, `integrity_basic.json`, `integrity_signed.json`)
- **Test vectors**: `test-vectors/`

### Example JSON payload (HSI 1.3)

```json
{
  "hsi_version": "1.3",
  "observed_at_utc": "2026-05-01T09:01:00Z",
  "computed_at_utc": "2026-05-01T09:01:00Z",
  "producer": { "name": "Example Producer", "version": "1.3.0" },
  "windows": {
    "w1": { "start_utc": "2026-05-01T09:00:00Z", "end_utc": "2026-05-01T09:01:00Z" }
  },
  "axes": {
    "physiological": [
      {
        "name": "strain", "score": 0.42, "confidence": 0.6,
        "direction": "higher_is_more",
        "inference_mode": "deterministic_rule",
        "model_id": "rulepack://strain_v1",
        "window_ids": ["w1"], "evidence_source_ids": ["s_wear"]
      }
    ],
    "kinematic": [
      {
        "name": "activity_state", "score": null,
        "label": "walking",
        "categories": ["sedentary", "standing", "walking", "running"],
        "confidence": 0.78, "direction": "categorical",
        "inference_mode": "deterministic_rule",
        "model_id": "rulepack://activity_state_v1",
        "window_ids": ["w1"], "evidence_source_ids": ["s_wear"]
      }
    ],
    "cognitive": [
      {
        "name": "focus", "score": 0.65, "confidence": 0.7,
        "direction": "higher_is_more",
        "modalities_used": ["physiological", "digital"],
        "confidence_breakdown": { "physiological": 0.75, "digital": 0.65 },
        "inference_mode": "composite",
        "model_id": "rulepack://focus_v1",
        "window_ids": ["w1"], "evidence_source_ids": ["s_wear", "s_phone"]
      }
    ]
  },
  "privacy": {
    "contains_pii": false,
    "raw_biosignals_allowed": false,
    "derived_metrics_allowed": true
  },
  "meta": {
    "provenance": {
      "sources": {
        "s_wear":  { "type": "sensor", "quality": 0.9, "degraded": false, "source_tier": 2, "device_class": "watch", "signals": ["ppg","hrv"] },
        "s_phone": { "type": "sensor", "quality": 0.9, "degraded": false, "source_tier": 3, "device_class": "phone", "signals": ["touch"] }
      }
    }
  }
}
```

See `examples/valid/runtime_snapshot_1_3.json` for a full payload exercising all five axis domains, `confidence_breakdown` on multimodal readings, the categorical reading shape, and the optional `integrity` block.

### Notes on axes, null readings, and embeddings

- **Axis domains (HSI 1.3)**: closed 5-domain set under `axes`: `physiological` (biosignals), `kinematic` (motion), `digital` (OS-event interaction), `cognitive` (multimodal fusion), `affective` (multimodal fusion). The 1.2 domains `behavior`, `engagement`, `context`, `emotion` are dissolved with migration mappings in RFC-HSI-0010 §11.
- **Modality attribution**: readings in `axes.cognitive[]` and `axes.affective[]` MUST include `modalities_used` (array of `physiological` / `kinematic` / `digital`). Single-modality readings MUST NOT — the parent domain key already encodes the channel.
- **Per-channel confidence (optional)**: multimodal readings MAY carry `axis_reading.confidence_breakdown` mapping each contributing modality to a `[0, 1]` confidence value, capturing the producer's certainty in each channel's contribution to the fused output (RFC-HSI-0011). Provisional in 1.3.
- **Categorical readings**: when `direction: "categorical"`, the reading carries `label` + `categories` and `score` MUST be `null` (RFC-HSI-0010 §8). Use for kinematic class outputs (`activity_state`, `postural_state`, `locomotion_state`).
- **Source descriptors**: each entry in `meta.provenance.sources` carries `type`, `quality`, `degraded`, optional `source_tier` (architectural fidelity 1–4, carried over from 1.2), and the PR #5 descriptors (`device_class`, `signals`, `transport`, `vendor`). Non-empty `evidence_source_ids` SHOULD reference these keys.
- **Null readings**: a producer MAY include an axis reading with `score: null` when the reading is unavailable. A null score MUST be accompanied by a `meta` explanation and MUST NOT be interpreted as zero. Categorical readings have structurally null `score` and do not require additional explanation.
- **Embeddings**: if `embeddings[]` is present, each embedding includes `dimension`, `encoding`, and `confidence`, and includes at least one of `vector` and/or `vector_hash`. Consumers MUST NOT assume vectors are always present.
- **Integrity block (optional)**: producers needing tamper-evidence MAY include a top-level `integrity` object with `canonicalization` + `content_hash` (and optional detached `signature`) per RFC-HSI-0009. Reference BASIC and STRICT validators don't recompute the hash — that's the HSI-VALIDATE-INTEGRITY tier.

---

## Testing & CI

This repo includes a small test suite that validates:

- **HSI-VALIDATE-BASIC**: Draft 2020-12 structural + range validation. Schema is selected per payload's declared `hsi_version` — `schema/hsi-1.3.schema.json` is canonical; 1.0 / 1.1 / 1.2 schemas are retained for older payloads.
- **HSI-VALIDATE-STRICT**: additional cross-field integrity checks (e.g., `window_id` references, time ordering, modalities_used placement, categorical-label-in-categories, confidence_breakdown subset rule).
- **HSI-VALIDATE-INTEGRITY** (optional, RFC-HSI-0009 §7): recomputes `integrity.content_hash` over the canonicalized payload (with `integrity` removed) and verifies any detached `signature`. Requires a JCS canonicalizer and trust policy; not exercised by the reference validator.

Run locally:

```bash
# macOS/Homebrew note: pip may refuse system installs (PEP 668). Use a venv.
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

### Privacy and scope notes

- **No PII**: Producers MUST NOT emit personally identifying information. See `SECURITY.md`.

### Patent notice

This repository is licensed under **Apache-2.0**, which includes an **express patent license grant** from contributors and a **patent retaliation / termination** provision. See `LICENSE` (Section 3) and `NOTICE`.

---

## Reference Implementations

HSI is an interface specification only. Multiple independent systems may
implement HSI producers or consumers.

### Synheart Core (Reference Implementation)

Synheart Core is a **privacy-first, on-device implementation** that produces
and consumes HSI-compliant payloads. It is provided as a reference example,
not a requirement. It includes:

- **HSI Runtime**: On-device human state fusion and inference
- **Multi-Modal Data Collection**: Wearables, phone sensors, and behavioral signals
- **Privacy-First**: Zero raw data, consent-gated, capability-based
- **Multi-Platform**: Flutter/Dart, Android/Kotlin, iOS/Swift

📦 **Repository**: [Synheart Core](https://github.com/synheart-ai/synheart-core)

#### Platform SDKs

| Platform | Language | Repository | Package |
|----------|----------|------------|---------|
| **Flutter** | Dart | [synheart-core-dart](https://github.com/synheart-ai/synheart-core-dart) | `synheart_core` |
| **Android** | Kotlin | [synheart-core-kotlin](https://github.com/synheart-ai/synheart-core-kotlin) | `ai.synheart:core-sdk` |
| **iOS** | Swift | [synheart-core-swift](https://github.com/synheart-ai/synheart-core-swift) | `SynheartCore` |

## Governance & Evolution

HSI evolves through a lightweight RFC process.

- All breaking changes require a new `hsi_version`
- Backward-compatible additions are permitted within a minor revision
- RFCs are reviewed in public and merged by consensus
- This repository defines the canonical contract, independent of any implementation

No single implementation (including Synheart Core) defines HSI behavior.


See the [Synheart Core documentation](https://docs.synheart.ai) for complete integration guides.

---


