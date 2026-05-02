## Human State Interface (HSI)

[![Version](https://img.shields.io/badge/version-1.3-blue.svg)](schema/hsi-1.3.schema.json)
[![Schema](https://img.shields.io/badge/schema-JSON%20Draft%202020--12-green.svg)](https://json-schema.org/draft/2020-12/schema)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![RFC](https://img.shields.io/badge/RFC--HSI--0008-1.2_canonical-purple.svg)](docs/RFC-HSI-0008.md)
[![RFC](https://img.shields.io/badge/RFC--HSI--0010-1.3_axes_modalities-purple.svg)](docs/RFC-HSI-0010.md)
[![RFC](https://img.shields.io/badge/RFC--HSI--0011-1.3_tiers-purple.svg)](docs/RFC-HSI-0011.md)
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

- **Authoritative RFC (HSI 1.2)**: [`docs/RFC-HSI-0008.md`](docs/RFC-HSI-0008.md) — canonical 1.2 contract; supersedes RFC-0005 and folds in RFC-HSI-0007
- **Historical RFC (HSI 1.0)**: [`docs/RFC-0005-hsi-canonical-contract.md`](docs/RFC-0005-hsi-canonical-contract.md)
- **Context axis guidance**: [`docs/RFC-HSI-0006.md`](docs/RFC-HSI-0006.md)
- **Draft RFC (HSI 1.3, proposed)**: [`docs/RFC-HSI-0009.md`](docs/RFC-HSI-0009.md) — optional payload integrity block (content hash + detached signature)
- **Validation schema (HSI 1.2, canonical)**: `schema/hsi-1.2.schema.json`
- **Earlier schemas**: `schema/hsi-1.1.schema.json`, `schema/hsi-1.0.schema.json` — retained for historical payloads
- **Versioning policy**: `versioning.md`
- **Security and privacy**: `SECURITY.md`
- **Examples**: `examples/`
- **Test vectors**: `test-vectors/`

### Example JSON payload

```json
{
  "hsi_version": "1.2",
  "observed_at_utc": "2025-12-28T00:00:10Z",
  "computed_at_utc": "2025-12-28T00:00:10Z",
  "producer": {
    "name": "Example Producer",
    "version": "1.0.0",
    "instance_id": "0b6f3ac9-62f5-4c9f-9f0d-4c4b3f6b2a3b"
  },
  "windows": {
    "w1": {
      "start_utc": "2025-12-28T00:00:00Z",
      "end_utc": "2025-12-28T00:00:10Z",
      "label": "10s_window"
    }
  },
  "axes": {
    "physiological": [
      {
        "name": "valence",
        "score": 0.62,
        "confidence": 0.71,
        "direction": "higher_is_more",
        "inference_mode": "probabilistic_model",
        "model_id": "model://example/valence-v1",
        "window_ids": ["w1"],
        "evidence_source_ids": []
      },
      {
        "name": "arousal",
        "score": 0.44,
        "confidence": 0.68,
        "direction": "higher_is_more",
        "inference_mode": "probabilistic_model",
        "model_id": "model://example/arousal-v1",
        "window_ids": ["w1"],
        "evidence_source_ids": []
      }
    ],
    "context": [
      {
        "name": "activity_still_conf",
        "score": 0.93,
        "confidence": 0.88,
        "direction": "higher_is_more",
        "inference_mode": "deterministic_rule",
        "model_id": "rulepack://context_activity_v1",
        "window_ids": ["w1"],
        "evidence_source_ids": []
      },
      {
        "name": "baseline_ready",
        "score": 1,
        "confidence": 1.0,
        "direction": "higher_is_more",
        "inference_mode": "deterministic_rule",
        "model_id": "rulepack://baseline_flags_v1",
        "window_ids": ["w1"],
        "evidence_source_ids": []
      }
    ]
  },
  "privacy": {
    "contains_pii": false,
    "raw_biosignals_allowed": false,
    "derived_metrics_allowed": true,
    "notes": "No PII; physiological + context payload."
  },
  "meta": {
    "intent": "Valid example: physiological + context domains."
  }
}
```

### Notes on axes, null readings, and embeddings

- **Axis domains**: HSI 1.2 lists readings under `axes.physiological`, `axes.behavior`, `axes.engagement`, `axes.context`, and optional `axes.emotion` (each domain is an array of readings). The context domain carries numeric runtime-condition qualifiers used to interpret other axes (RFC-HSI-0006). Non-empty `evidence_source_ids` SHOULD reference keys in `meta.provenance.sources`.
- **Null readings**: A producer MAY include an axis reading with `score: null` when the reading is unavailable (e.g., access-control, missing sources). A null score MUST be accompanied by an explanation (typically in `meta`) and MUST NOT be interpreted as zero.
- **Embeddings**: If `embeddings[]` is present, each embedding includes `dimension`, `encoding`, and `confidence`, and includes at least one of `vector` and/or `vector_hash`. Consumers MUST NOT assume vectors are always present.

---

## Testing & CI

This repo includes a small test suite that validates:

- **HSI-VALIDATE-BASIC**: Draft 2020-12 structural + range validation against `schema/hsi-1.2.schema.json`
- **HSI-VALIDATE-STRICT**: additional cross-field integrity checks (e.g., `window_id` references, time ordering)

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


