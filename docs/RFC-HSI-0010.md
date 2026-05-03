# RFC-HSI-0010

## HSI 1.3 — Canonical 5-Axis Domain Set and Modality Model

- **Status**: Draft
- **Type**: Minor (breaking under pre-stable; see `versioning.md`)
- **Target**: HSI 1.3
- **Owner**: HSI Maintainers
- **Paired with**: RFC-HSI-0011 (per-modality fidelity tiers). 0010 + 0011 are a single 1.3 change; both MUST be Accepted before the 1.3 schema PR proceeds.
- **Depends on**: PR #5 against `synheart-ai/hsi` (1.2 source descriptors: `device_class`, `signals`, `transport`, `vendor`). PR #5 MUST land before the 1.3 schema PR.
- **Relates to**: RFC-HSI-0008 (HSI 1.2 canonical contract), RFC-HSI-0006 (1.1 context domain), RFC-HSI-0009 (HSI 1.3 integrity block, independent)
- **Canonical schema**: `schema/hsi-1.3.schema.json` (added when this RFC is Accepted)

## 1. Purpose

HSI 1.0–1.2 defines axis domains (`physiological`, `behavior`, `engagement`, `context`, `emotion`) that grew from operational need rather than a coherent model of what the axes describe. As HSI is consumed by a wider set of producers and consumers — wearables, mobile apps, desktop and web clients, behavioral analytics, affective computing — three problems have surfaced:

1. **Domain overlap and ambiguity.** `behavior` mixes body movement (kinematic) with device interaction (OS events). `engagement` mixes attentional state (cognitive) with interaction pattern (digital). Producers cannot consistently choose where a reading belongs; consumers cannot reliably interpret across producers.
2. **Missing modality attribution.** A reading carries `evidence_source_ids` referencing source descriptors that themselves declare a `source_tier`, but consumers cannot tell which *channels of observation* (biosensor, motion, OS events, fusion) the producer relied on to compute it. This matters because the same axis name (e.g. `focus`) can be inferred from very different evidence: a wearable producer infers it from HRV; a desktop-only producer infers it from interaction rhythm. Consumers need to know which.
3. **No standard for categorical axes.** Activity class, postural class, and locomotion class are not points on a `[0, 1]` scale. The current `axis_reading` shape forces producers to encode them as `score`, breaking the semantic of the field, or to omit them entirely.

HSI 1.3 reorganizes axes around **what kind of human-state dimension is being described** and **which modality of observation produced it**. Five canonical axis domains and four canonical modalities are introduced as the v1 vocabulary. Per-reading modality attribution is required. The `direction` enum is extended to include `categorical`, and a categorical reading shape is defined.

This is a deliberate restructuring under HSI's pre-stable regime (`versioning.md`). Existing 1.2 payloads remain validatable against `schema/hsi-1.2.schema.json`; producers that adopt 1.3 emit the new shape.

## 2. Non-goals

- **Per-channel confidence attribution.** A separate RFC (RFC-HSI-0011) defines `axis_reading.confidence_breakdown`, an optional per-modality confidence map on multimodal readings. This RFC takes no position on its shape; consumers and producers should treat the two RFCs as a paired 1.3 change. (RFC-HSI-0011 was revised during 1.3 review: the earlier `tiers` design was rejected, and the 1.2 `source_tier` field is removed in 1.3 with no source-level replacement.)
- **Closed axis-name vocabularies.** Each domain lists v1 canonical members, but unknown axis names within a known domain MUST be tolerated per RFC-HSI-0008 §6.5 and `versioning.md`.
- **Raw-signal transport.** HSI carries inferred state, not raw biosignals or feature vectors. §10 makes this an explicit normative constraint.
- **Inference-method standardization.** Producers remain free to use rulepacks, learned models, or composites; `inference_mode` (RFC-HSI-0008 §6.3) continues to describe the method independently of `modality` (which describes the input channel).
- **The HSI 1.3 integrity block** (RFC-HSI-0009). Independent addition; both land in 1.3.

## 3. Relation to prior RFCs

- **RFC-HSI-0008** is the HSI 1.2 canonical contract. Its axis-reading shape, source/provenance model, embeddings, privacy, temporal, and compliance rules are inherited unchanged unless this RFC modifies them. Modifications: §4 (axis domains), §5 (axis-reading shape additions), §7 (direction enum), §8 (categorical reading shape).
- **RFC-HSI-0007** introduced the optional `axes.emotion` domain. HSI 1.3 supersedes that placement: emotion-class readings move into the `affective` axis as named members (`valence`, `arousal`, `stress`).
- **RFC-HSI-0006** introduced `axes.context`. HSI 1.3 dissolves the `context` domain; runtime-context information lives in `meta.provenance` and `source` descriptors. See §11.5 for migration guidance.
- **RFC-HSI-0009** adds the optional `integrity` block in HSI 1.3. This RFC is independent and additive over that work; both land in `schema/hsi-1.3.schema.json`.

## 4. Canonical axis domains

HSI 1.3 defines exactly five canonical axis domains. The schema's `additionalProperties: false` on the `axes` object enforces this set; adding a domain requires a schema update and a new RFC.

| Domain | Question | Nature |
|---|---|---|
| `physiological` | What is happening inside the body right now? | Directly inferred from biosignals (HR, RR intervals, derived HRV). |
| `kinematic` | What is the body doing in the physical world? | Directly inferred from motion sensors (accelerometer, gyroscope). |
| `digital` | How is the person interacting with their digital environment? | Directly inferred from OS events (taps, keystrokes, scrolls, app switches, notifications). |
| `cognitive` | What is the mind's current processing condition? | Multimodal inference. |
| `affective` | What is the person's current emotional experience? | Multimodal inference. |

Each domain is a plain array of axis readings, identical in shape to RFC-HSI-0008 §6.2 with the additions defined in §5 below.

### 4.1 Physiological axis members (v1 canonical)

The body's biological state, observable from biosensor evidence only.

- **`strain`** — degree of physiological load currently carried by the body. Reflects accumulated demand on the autonomic nervous system from physical, cognitive, or emotional sources. Direction: `higher_is_more`.
- **`recovery`** — body's progress in restoring biological homeostasis after accumulated strain. Driven by parasympathetic reassertion. Direction: `higher_is_more`.
- **`sleep_score`** — biological restoration that occurred during the most recent sleep period, as readable in the morning HRV signature. Direction: `higher_is_more`.
- **`readiness`** — body's overall biological preparedness to handle physical or cognitive demand at this moment. Synthesizes `strain`, `recovery`, and `sleep_score`. Direction: `higher_is_more`.
- **`acute_stress_response`** — body's automatic autonomic stress response (HR elevation, RMSSD suppression, sympathetic dominance) firing in response to a stimulus. Distinct from `affective.stress` (subjective experience requiring conscious appraisal): the body can have `acute_stress_response: 0.9` (e.g. driving an emergency) while `affective.stress` is low (experienced driver, in control). Conflating these two states produces incorrect adaptive-system interventions. Direction: `higher_is_more`.

### 4.2 Kinematic axis members (v1 canonical)

The body's external position, posture, and movement in physical space.

- **`activity_state`** — current category of physical activity (categorical: `sedentary`, `standing`, `walking`, `running`, `cycling`, `vigorous`). Direction: `categorical`.
- **`postural_state`** — body's current orientation in gravitational space (categorical: `lying`, `sitting`, `standing`, `in_motion`). Direction: `categorical`. Critical for interpreting physiological signals (orthostatic response).
- **`locomotion_state`** — whether and how the body is moving through physical space (categorical: `stationary`, `walking`, `running`, `in_vehicle`, `ascending`, `descending`). Distinct from `activity_state`: a person in a vehicle has locomotion without personal exertion; a person on a treadmill has activity without locomotion. Direction: `categorical`.
- **`movement_regularity`** — smoothness, consistency, and periodicity of body movement over the window. Direction: `higher_is_more`.

### 4.3 Digital interaction axis members (v1 canonical)

Body-device interaction patterns observable from OS event streams. **Conditional**: present only when device interaction is occurring; absent during sleep, exercise, driving, face-to-face conversation, or full-screen contexts.

- **`focus_quality`** — degree to which the interaction pattern reflects sustained, uninterrupted digital engagement over the window. The interaction pattern observable from the device — not the cognitive state itself. A person on autopilot can produce high `focus_quality` while cognitively disengaged. Direction: `higher_is_more`.
- **`interruption_pressure`** — load of external digital interruptions on the person's attention budget over the window. The digital environment's *demand* on attention, distinct from how the person responds. Direction: `lower_is_more`.
- **`cognitive_friction`** — observable difficulty and error rate in digital interaction over the window (correction rate, editing friction, scroll jitter, task-switch cost). Behavioral signal of interaction-quality degradation, not a direct measure of cognitive state. Direction: `lower_is_more`.
- **`interaction_mode`** — overall rhythm of digital interaction over the window, on a spectrum from reactive (burst-idle-burst, event-driven) to deliberate (sustained, steady). Direction: `bidirectional`. Neither end is inherently better; mode-task mismatch is itself a signal.

### 4.4 Cognitive axis members (v1 canonical)

The mind's current processing condition. Always inferred — never directly measurable. Performance-oriented: describes what the mind *can do*, not what the person feels. Confidence proportional to modality availability.

- **`focus`** — degree to which the mind is in a state of sustained, directed attention. Distinct from `digital.focus_quality`: that is the observable interaction pattern; this is the mind's actual attentional state. A reading can have high `focus_quality` with low `focus` (autopilot). Direction: `higher_is_more`.
- **`cognitive_load`** — current demand on working memory and processing resources relative to available capacity. Optimal zone is moderate. Direction: `lower_is_more`. Synonym `mental_effort` is permitted but `cognitive_load` is the canonical name.
- **`mental_fatigue`** — depletion of cognitive processing resources through sustained mental effort. Distinct from physiological fatigue (body depletion) and affective tiredness (feeling tired). Direction: `lower_is_more`.
- **`capacity`** — current available cognitive processing headroom — gap between current `cognitive_load` and maximum processing capability. Synthesis member of the cognitive axis. Direction: `higher_is_more`.

### 4.5 Affective axis members (v1 canonical)

The person's current emotional experience. Always inferred. Highest uncertainty of all five axes due to the inherently subjective nature of emotional experience.

- **`valence`** — positive (pleasant, approach-oriented) vs negative (unpleasant, avoidance-oriented) quality of current emotional experience. First fundamental dimension of the affective circumplex (Russell, 1980). Direction: `bidirectional`.
- **`arousal`** — activated (excited, alert) vs deactivated (calm, drowsy) quality of current emotional experience. Second fundamental dimension of the affective circumplex. Direction: `bidirectional`. Critically distinct from physiological strain — high subjective arousal can co-occur with low physiological strain and vice versa.
- **`stress`** — subjective experience of feeling overwhelmed, threatened, or unable to cope. Requires cognitive appraisal. Distinct from `physiological.acute_stress_response` (which fires before conscious awareness and requires no appraisal). See §4.1 for the worked-example contrast. Direction: `lower_is_more`.

### 4.6 Axis naming guidance

Producers SHOULD use the canonical member names in §4.1–§4.5 when emitting a member that matches one of the canonical concepts. Unknown names within a known domain MUST be tolerated (RFC-HSI-0008 §6.5). New canonical members are added by RFC.

Names MUST be `lower_snake_case`. The legacy 1.2 emotion-class naming (`emotion.stress`, `emotion.calm`, etc.) is superseded; in 1.3 these are members of the `affective` domain (`stress` etc.) without the `emotion.` prefix. See §11.4.

## 5. Modality attribution

Modality attribution in 1.3 is **encoded by the axis domain key** (RFC-HSI-0010 §4): a reading's containing domain determines its observation channel. Single-modality readings (in `axes.physiological[]`, `axes.kinematic[]`, `axes.digital[]`) need no further attribution. Multimodal readings (in `axes.cognitive[]`, `axes.affective[]`) carry an explicit list of contributing channels.

### 5.1 The `modalities_used` field

- **`modalities_used`** (array of strings, conditional): list of contributing modalities. **Required on every reading in `axes.cognitive[]` and `axes.affective[]`**; forbidden on readings in the three single-modality domains. Entries MUST be drawn from the canonical observable modalities (`physiological`, `kinematic`, `digital`); a multimodal reading cannot list `multimodal` as a contributor. MUST contain at least one entry. Order is non-significant; uniqueness enforced.

### 5.2 No standalone `modality` field

Earlier drafts of this RFC defined a required scalar `modality` field on every axis_reading. That field was removed because its value is fully determined by the axis domain (`axes.<domain>` → modality) and would have been pure redundancy on every payload. Consumers determine the modality of a reading by inspecting which axis domain it appears in; for readings in the multimodal domains (`cognitive`, `affective`), the contributing channels are read from `modalities_used`.

### 5.3 Independence from `inference_mode`

A reading's modality (encoded by its domain) describes the **input channel**; `inference_mode` (RFC-HSI-0008 §6.3) describes the **inference method**. They are orthogonal:

- A `physiological` reading with `inference_mode: deterministic_rule` — rulepack on HRV.
- A `physiological` reading with `inference_mode: probabilistic_model` — ONNX on HRV.
- A `cognitive` reading with `modalities_used: ["physiological", "digital"]` and `inference_mode: composite` — fusion of HRV + interaction patterns with a learned weighting.

`inference_mode` is required on every axis_reading per RFC-HSI-0008 §6.2; this RFC does not change that.

## 6. The four canonical modalities

A modality is a distinct channel through which human-state evidence is collected, defined by its source, the type of reality it observes, and when it is present.

| Modality | Source | Observes | Coverage | Absent when |
|---|---|---|---|---|
| `physiological` | Biosensor in skin contact (PPG, ECG, RR-bearing wearable). | Internal biological state of the body. | Universal whenever sensor contact is maintained. | Never, given contact. |
| `kinematic` | Motion sensor (accelerometer, optionally gyroscope/magnetometer). | External physical position and movement of the body in space. | Universal whenever sensor is worn or carried. | Never, given the device is on the body. |
| `digital` | Device OS event stream (phone, tablet, computer). | Body-device interaction patterns. | Conditional. | Sleeping, exercising without device interaction, driving, face-to-face conversation, full-screen passive consumption. |
| `multimodal` | Fusion of two or more observable modalities. | Higher-order inferred states no single modality can reveal. | Present when at least one observable modality is active; confidence proportional to modalities available. | Never computed without ≥1 observable modality. |

Modalities are a **closed v1 set**. Adding a new modality (e.g. `audio`, `eda`, `eeg` as a first-class observation channel rather than a feature within `physiological`) requires a new RFC and a schema bump.

### 6.1 Out-of-scope channels

The v1 modality set covers sensor-derived observation channels only. Two kinds of evidence are recognized by HSI but not represented as modalities in 1.3:

- **Self-report.** RFC-HSI-0008 source.type already includes `self_report` as a recognized source type (a user explicitly reporting their mood, an annotator labeling a session). Self-report has different semantics from sensor channels: no continuous coverage, no derivation chain, fidelity-tier ladders do not apply in the same shape. Producers emitting self-reported readings SHOULD attach `evidence_source_ids` referencing a source with `type: "self_report"` and SHOULD NOT force-fit the reading to one of the four canonical modalities. A future RFC may promote `self_report` to a fifth canonical modality once its tier semantics are settled.
- **Derived signals from third-party providers.** Already covered by RFC-HSI-0008 source.type `external_provider`; modality attribution for such readings follows the channel(s) the provider's output is treated as (typically `physiological` for vendor HRV).

## 7. Direction enum extension

The `direction` enum on `axis_reading` is extended:

- `higher_is_more` (unchanged) — higher score indicates more of the property.
- `lower_is_more` (renamed from `higher_is_less`) — lower score indicates more of the property.
- `bidirectional` (unchanged) — score is meaningful relative to a midpoint (typically 0.5); both directions of departure carry semantic load.
- **`categorical`** (new) — the reading carries a categorical class rather than a scalar score; see §8.

The rename `higher_is_less → lower_is_more` is a semantic clarification: the new name reads symmetrically against `higher_is_more` and matches the convention used in axis-member documentation. 1.3 producers MUST use `lower_is_more`. 1.2 payloads using `higher_is_less` continue to validate against `schema/hsi-1.2.schema.json`.

## 8. Categorical axis_reading shape

Some axis members (notably in `kinematic`: `activity_state`, `postural_state`, `locomotion_state`) are inherently categorical and cannot be represented as a `[0, 1]` score. RFC-HSI-0008 §6.2 explicitly forbids this case. HSI 1.3 lifts that restriction by introducing a categorical reading shape on the existing `axis_reading` object, gated by `direction == "categorical"`.

### 8.1 Field additions

When `direction == "categorical"`:

- **`label`** (string, required): the active category for this reading. MUST be `lower_snake_case`.
- **`categories`** (array of strings, required, `uniqueItems: true`, `minItems: 2`): the full set of possible categories the producer may emit for this axis member. MUST contain `label`.
- **`score`** (existing field): MUST be `null`. Consumers MUST NOT interpret as zero (RFC-HSI-0008 §6.6).

`label` and `categories` MUST NOT be present on readings whose `direction` is not `categorical`.

### 8.2 Confidence for categorical readings

`confidence` retains its standard meaning (RFC-HSI-0008 §6.2): the producer's certainty in the *correctness of the emitted reading* — for categorical readings, certainty in the chosen `label`. There is no `category_scores` field in 1.3; producers that need to expose per-category uncertainty MAY place it under producer-defined keys in `meta` and document the semantics out of band. A future RFC MAY introduce a normative per-category-distribution field once a real consumer use case is identified and the distribution semantics (independent likelihoods vs sum-to-one categorical) are settled.

## 9. Modality availability and required suppression

Producers MUST follow these rules for which axis members may be emitted given which modalities are available:

| Axis | Modality requirement |
|---|---|
| `axes.physiological[*]` | The `physiological` modality MUST be available (a producer placing readings here is asserting biosensor evidence). |
| `axes.kinematic[*]` | The `kinematic` modality MUST be available. |
| `axes.digital[*]` | The `digital` modality MUST be available. |
| `axes.cognitive[*]` | `modalities_used` MUST contain at least one of `physiological`, `kinematic`, `digital`. Confidence SHOULD reflect the number and fidelity of contributing modalities (RFC-HSI-0011 §5). |
| `axes.affective[*]` | `modalities_used` SHOULD contain `physiological`, OR contain both `kinematic` and `digital`. Affective members backed only by `digital` carry weaker evidence — affective valence and arousal are autonomic constructs and *typically* benefit from body-level signals — but research and atypical-deployment producers (e.g. sentiment from typing dynamics) MAY emit digital-only affective readings when their context justifies it. The OR/AND structure is a conservative producer-policy default, not a calibrated science result; the schema and reference STRICT validator do not enforce it. A future RFC may promote this to a normative MUST once calibration evidence supports a defensible rule. |

Producers MUST NOT emit a reading whose required modality is unavailable. They MAY emit `score: null` with a `meta.null_reading_reason` of `modality_unavailable` (RFC-HSI-0008 §6.6) instead, when consumers benefit from a placeholder (e.g. dashboards that render fixed axis lists).

## 10. The "no raw data in HSI" principle

HSI carries **inferred state**, not raw signals or feature vectors. The following SHALL NOT appear in HSI payloads:

- Raw biosignal samples (HR time series, RR intervals, accelerometer samples).
- Engine-internal feature scalars (RMSSD, SDNN, pNN50, LF/HF, DFA α1, SampEn, touch-rate per minute, burstiness, scroll-jitter rate, etc.).
- Per-feature provenance maps that name internal feature keys.

This rule is normative for 1.3 producers. Engine-internal features MAY be retained outside HSI for research export or producer-internal use, but they MUST NOT be embedded in an HSI payload to circumvent the contract.

This formalizes existing 1.2 practice. The 1.2 schema does not enforce the rule structurally (it would require enumerating forbidden names), but the strict validator MAY add a "no raw feature names in axis names" lint pass.

## 11. Migration from HSI 1.2

HSI 1.3 reorganizes the axis domain set. Producers migrating from 1.2 follow this mapping.

### 11.1 `physiological`

- Members in `axes.physiological[]` carry over unchanged in name and shape. No `modality` field to add (§5.2).

### 11.2 `behavior` (dissolved)

- Movement-derived members (movement regularity, activity classification, posture) move to `axes.kinematic[]`.
- OS-event-derived members (interaction intensity, attention, task persistence, focus quality, interruption load, cognitive friction, interaction mode) move to `axes.digital[]`.
- Producers SHOULD use the canonical 1.3 names where they apply (§4.2, §4.3) and MAY retain non-canonical names with the same domain assignment.

### 11.3 `engagement` (dissolved)

- Cognitive-attention members (engagement_level, engagement_stability, absorption, focus, capacity) move to `axes.cognitive[]` with a populated `modalities_used` declaring which channels contributed.
- Interaction-pattern members (focus_quality if previously placed in engagement) move to `axes.digital[]`.

### 11.4 `emotion` → `affective`

- The optional 1.2 `axes.emotion[]` domain is renamed `axes.affective[]`.
- The 1.2 prefix convention (`emotion.stress`, `emotion.calm`) is dropped: 1.3 emotion-class names are bare (`stress`, `calm`).
- Producers that emitted `valence`/`arousal` as members of `axes.physiological[]` (1.2 §6.5 example) MUST move them to `axes.affective[]` in 1.3 and populate `modalities_used`. Affective valence and arousal are not directly observable physiological states.
- 1.2 emotion-class names that do not map to a 1.3 canonical affective member (`calm`, `joy`, etc. — see RFC-HSI-0008 §6.4) MAY remain as non-canonical members of `axes.affective[]` per RFC-HSI-0008 §6.5 (unknown axis names within a known domain MUST be tolerated). A future RFC may consolidate these into the canonical valence/arousal/stress shape.

### 11.5 `context` (dissolved)

- The 1.2 `axes.context[]` domain (RFC-HSI-0006) is dissolved.
- Numeric activity-confidence axes (`activity_still_conf`, `activity_walk_conf`, etc.) are subsumed by `axes.kinematic[].activity_state` with `direction: "categorical"` and per-category scores (§8.2).
- Sleep-episode and baseline-readiness flags (`sleep_episode_active`, `baseline_ready`, `baseline_maturity`) move to `meta.provenance` as producer-defined fields. They are runtime-context for interpretation, not human-state readings.
- Boolean/0-1 activity-state flags become categorical (§4.2, §8).

### 11.6 Direction rename

- 1.2 `direction: "higher_is_less"` → 1.3 `direction: "lower_is_more"`.
- 1.3 schemas reject `higher_is_less`; 1.2 schemas continue to accept it. Producers cross-emitting MUST emit per the version they declare in `hsi_version`.

### 11.7 Producer migration sequence

1. Reorganize axes into the new domain set per §11.1–§11.5.
2. Populate `modalities_used` on every reading in `axes.cognitive[]` and `axes.affective[]`.
3. Convert categorical kinematic readings to the §8 shape (`label`, `categories`, `score: null`, `direction: "categorical"`).
4. Rename `higher_is_less` → `lower_is_more`.
5. Move 1.2 `context` axes into `meta.provenance` or `kinematic` as applicable (§11.5).
6. Keep `source.source_tier` on every applicable entry in `meta.provenance.sources` exactly as in 1.2 (carried over per RFC-HSI-0011 §3). Optionally adopt `axis_reading.confidence_breakdown` on multimodal readings (RFC-HSI-0011 §4).
7. Set `hsi_version: "1.3"`.

Producers MAY emit 1.2 and 1.3 in parallel during a transition period; consumers MUST validate each payload against the schema matching its declared `hsi_version`.

## 12. Compliance

- **HSI-VALIDATE-BASIC**: validates structural and range constraints against `schema/hsi-1.3.schema.json` using a Draft 2020-12 validator. Enforces:
  - Closed `axes` property set: only `physiological`, `kinematic`, `digital`, `cognitive`, `affective`.
  - `direction` enum membership including `categorical` and `lower_is_more`; rejection of `higher_is_less`.
  - `if/then/else` discriminator on `direction == "categorical"`: when categorical, `label` and `categories` are required and `score` MUST be `null`; when not categorical, `label` and `categories` MUST be absent.
  - `modalities_used` shape (array, uniqueItems, items in `["physiological", "kinematic", "digital"]`, minItems 1) where present.
- **HSI-VALIDATE-STRICT**: BASIC plus reference-integrity and consistency checks enforced in code (`tests/hsi_validate.py::_validate_strict_13`):
  - All RFC-HSI-0008 §10 STRICT checks remain.
  - **`modalities_used` required-on-multimodal-domains**: every reading in `axes.cognitive[]` and `axes.affective[]` MUST include `modalities_used`. Violation: HSI-1.3-MODALITIES-USED-MISSING.
  - **`modalities_used` forbidden-on-single-modality-domains**: readings in `axes.physiological[]`, `axes.kinematic[]`, and `axes.digital[]` MUST NOT include `modalities_used` (the domain key already encodes the modality). Violation: HSI-1.3-MODALITIES-USED-FORBIDDEN.
  - **Categorical reading integrity** (§8): `label` MUST appear in `categories`.

The §9 affective-availability rule is *not* enforced at STRICT in 1.3. It is a producer-policy SHOULD pending calibration; legitimate research producers may emit digital-only affective readings without triggering a STRICT failure. A future RFC may promote it once data supports a defensible rule.

## 13. Schema additions

This section enumerates the concrete `schema/hsi-1.3.schema.json` changes relative to `schema/hsi-1.2.schema.json`. The full schema is materialized in the schema PR that lands when this RFC is Accepted.

### 13.1 `$defs` additions

```json
"observable_modality": {
  "type": "string",
  "enum": ["physiological", "kinematic", "digital"]
},

"direction": {
  "type": "string",
  "enum": ["higher_is_more", "lower_is_more", "bidirectional", "categorical"]
}
```

The 1.2 `direction` definition is replaced; `higher_is_less` is removed.

There is no standalone `modality` `$def` in 1.3. Modality is encoded by the axis domain key (§5.2). `observable_modality` is referenced by `modalities_used` and excludes `multimodal` (a multimodal reading cannot list itself as a contributor).

### 13.2 `axis_reading` additions

```json
"modalities_used": {
  "type": "array",
  "uniqueItems": true,
  "minItems": 1,
  "items": { "$ref": "#/$defs/observable_modality" }
},
"label":      { "type": "string", "pattern": "^[a-z][a-z0-9_]*$" },
"categories": {
  "type": "array",
  "uniqueItems": true,
  "minItems": 2,
  "items": { "type": "string", "pattern": "^[a-z][a-z0-9_]*$" }
}
```

`if`/`then`/`else` discriminator on `direction == "categorical"` expresses the scalar-vs-categorical split as a proper discriminated union:

```json
"if": {
  "properties": { "direction": { "const": "categorical" } },
  "required": ["direction"]
},
"then": {
  "required": ["label", "categories"],
  "properties": { "score": { "type": "null" } }
},
"else": {
  "not": {
    "anyOf": [
      { "required": ["label"] },
      { "required": ["categories"] }
    ]
  }
}
```

`modalities_used` placement (required on cognitive/affective, forbidden elsewhere) is enforced at the axes-domain level rather than on `axis_reading` itself, because the rule depends on which domain key the reading appears under. The construct is two distinct domain `$defs` (`axes_domain_single_modality` / `axes_domain_multimodal`, see §13.3) that each wrap `axis_reading` in an `allOf` adding a `required: ["modalities_used"]` rule (multimodal wrapper) or a `not: { anyOf: [{ required: ["modalities_used"] }, { required: ["confidence_breakdown"] }] }` rule (single-modality wrapper). The alternative — pushing the constraint into `axis_reading` and discriminating on the parent path — is not expressible in JSON Schema and is delegated to HSI-VALIDATE-STRICT (§12).

### 13.3 `axes` redefinition

```json
"axes": {
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "physiological": { "$ref": "#/$defs/axes_domain_single_modality" },
    "kinematic":     { "$ref": "#/$defs/axes_domain_single_modality" },
    "digital":       { "$ref": "#/$defs/axes_domain_single_modality" },
    "cognitive":     { "$ref": "#/$defs/axes_domain_multimodal" },
    "affective":     { "$ref": "#/$defs/axes_domain_multimodal" }
  }
}
```

The single-modality / multimodal split is realized by two distinct domain `$defs`. Each wraps `axis_reading` in an `allOf` that adds the modality-placement rule:

```json
"axes_domain_single_modality": {
  "type": "array",
  "items": {
    "allOf": [
      { "$ref": "#/$defs/axis_reading" },
      {
        "not": {
          "anyOf": [
            { "required": ["modalities_used"] },
            { "required": ["confidence_breakdown"] }
          ]
        }
      }
    ]
  }
},
"axes_domain_multimodal": {
  "type": "array",
  "items": {
    "allOf": [
      { "$ref": "#/$defs/axis_reading" },
      { "required": ["modalities_used"] }
    ]
  }
}
```

This is the construct that enforces (a) `modalities_used` is required on cognitive/affective and forbidden elsewhere (§5.1), and (b) `confidence_breakdown` from RFC-HSI-0011 is forbidden on single-modality readings.

The 1.2 properties `engagement`, `behavior`, `context`, `emotion` are removed.

### 13.4 Carry-overs

- The 1.2 single `axes_domain` `$def` is replaced by two domain `$defs` — `axes_domain_single_modality` and `axes_domain_multimodal` (§13.3) — to enforce the `modalities_used` placement rule at the schema level. The inner `axis_reading` shape is unchanged from 1.2 modulo the `modalities_used`, `confidence_breakdown`, `label`, `categories` additions and the extended `direction` enum; the wrapping is what's new.
- `source` descriptor unchanged from HSI 1.2 (post-PR #5). All 1.2 fields — `type`, `quality`, `degraded`, `source_tier`, `device_class`, `signals`, `transport`, `vendor`, `notes` — carry over with identical semantics. RFC-HSI-0011 originally proposed replacing `source_tier` with a per-modality `tiers` object; that draft was rejected and `source_tier` remains the canonical architectural-fidelity field on sources.
- `provenance` shape unchanged. Per-channel inference confidence on multimodal readings is expressed via `axis_reading.confidence_breakdown` (RFC-HSI-0011 §4); architectural channel fidelity continues to live on `source.source_tier`.
- `embedding` shape unchanged.
- All temporal, privacy, and producer fields unchanged.

## 14. Examples

`source.source_tier` (architectural fidelity) carries over from 1.2 unchanged and continues to live on each source descriptor. Per-channel inference confidence on multimodal readings is expressed inline on the reading via `axis_reading.confidence_breakdown` (RFC-HSI-0011 §4).

### 14.1 Multimodal cognitive axis (lives under `axes.cognitive[]`)

Reading:

```json
{
  "name": "focus",
  "score": 0.74,
  "confidence": 0.82,
  "direction": "higher_is_more",
  "modalities_used": ["physiological", "digital"],
  "confidence_breakdown": {
    "physiological": 0.85,
    "digital": 0.78
  },
  "inference_mode": "composite",
  "model_id": "rulepack://focus_v1",
  "window_ids": ["w-2026-05-01-0900-60s"],
  "evidence_source_ids": ["watch-ble-1", "phone-os-events"]
}
```

Cited sources in `meta.provenance.sources`:

```json
{
  "watch-ble-1":     { "type": "sensor", "quality": 0.9, "degraded": false, "source_tier": 2, "signals": ["ppg", "hrv"] },
  "phone-os-events": { "type": "sensor", "quality": 0.9, "degraded": false, "source_tier": 1, "signals": ["touch"] }
}
```

### 14.2 Categorical kinematic axis (lives under `axes.kinematic[]`)

```json
{
  "name": "activity_state",
  "score": null,
  "label": "walking",
  "categories": ["sedentary", "standing", "walking", "running", "cycling", "vigorous"],
  "confidence": 0.78,
  "direction": "categorical",
  "inference_mode": "deterministic_rule",
  "model_id": "rulepack://activity_state_v1",
  "window_ids": ["w-2026-05-01-0900-60s"],
  "evidence_source_ids": ["watch-accel"]
}
```

Cited source:

```json
{
  "watch-accel": { "type": "sensor", "quality": 0.9, "degraded": false, "source_tier": 1, "signals": ["accel", "gyro"] }
}
```

Single-modality reading; no `confidence_breakdown` (the parent domain key encodes the channel).

### 14.3 Digital-only axis, browser/desktop producer with no biosensor or motion (lives under `axes.digital[]`)

```json
{
  "name": "focus_quality",
  "score": 0.62,
  "confidence": 0.55,
  "direction": "higher_is_more",
  "inference_mode": "deterministic_rule",
  "model_id": "rulepack://focus_quality_v1",
  "window_ids": ["w-2026-05-01-1430-300s"],
  "evidence_source_ids": ["desktop-os-events"]
}
```

Cited source:

```json
{
  "desktop-os-events": { "type": "sensor", "quality": 0.85, "degraded": false, "source_tier": 1, "signals": ["touch"] }
}
```

`source_tier: 1` here means "ground-truth interaction events" — raw OS event stream with no upstream aggregation. `source.signals` not containing any biosignal token (`ppg`, `hrv`, etc.) makes "no physiological signal" obvious to consumers regardless of tier.

Note in all three: readings do not carry a source-level tier or a `modality` field. The reading's modality is encoded by which `axes.<domain>` array it appears in (§5.2). The multimodal reading in §14.1 carries `modalities_used` and (optionally) `confidence_breakdown`; the two single-modality readings carry neither.

## 15. Privacy considerations

- Modality attribution itself is metadata, not behavioral content; it does not weaken `privacy.contains_pii: false`.
- `digital` readings can correlate with app-usage patterns. Producers MUST continue to follow RFC-HSI-0008 §9 — no app names, no URLs, no free-text content from interaction events.
- Categorical kinematic labels (`activity_state`, `postural_state`, `locomotion_state`) carry coarse activity inference. They are not PII per GDPR/HIPAA but, combined with sufficient temporal granularity, MAY enable lifestyle inference. Producers SHOULD aggregate to the coarsest temporal window consistent with the consumer's purpose, and SHOULD avoid emitting sub-second locomotion readings outside research contexts with explicit consent.
- The `affective` domain inherits the privacy posture of the 1.2 `emotion` domain: emotional readings are sensitive and producers SHOULD restrict distribution.

## 16. Open questions

Before promoting this RFC to Accepted:

- **`mental_effort` synonym**: register `mental_effort` as a permitted alias for `cognitive_load` in the canonical-name guidance, or insist on a single name? Current draft permits both with `cognitive_load` as canonical. A stricter stance would simplify dashboards.
- **`context` dissolution timing**: dissolve in 1.3 (current draft) or retain `axes.context` for one minor as a deprecated domain to ease migration? RFC-HSI-0006 producers will need to migrate at the 1.3 cut.
- **Closed v1 modality set**: §6 defines the four canonical modalities as a closed set. Should `audio` (microphone-based valence/arousal) and `eeg` (EEG headsets) be reserved as future modalities now (with `MUST NOT emit until reserved`) or left as future RFC additions?
- **Affective availability rule**: §9 requires `physiological` OR (`kinematic` AND `digital`) for affective readings. The OR/AND structure is a conservative producer-policy default rather than a calibrated science result; should this RFC ship the rule as normative MUST or downgrade to SHOULD with producer discretion until calibration data exists?
- **Tier values comparable across modalities**: RFC-HSI-0011's per-modality tier integers all share the 1–N range and are NOT comparable across modalities. Should the schema enforce distinct value ranges (e.g. kinematic 11–13, digital 21–23), use enum strings instead of integers, or accept the existing footgun and rely on validator/documentation discipline? Decision affects RFC-HSI-0011 §4 and §8.1.

## 17. Canonical schema

When this RFC is Accepted, the changes in §13 are materialized in `schema/hsi-1.3.schema.json`, alongside RFC-HSI-0009's `integrity` block. `schema/hsi-1.2.schema.json` is unchanged; 1.2 payloads remain valid and MAY continue to be emitted.

The schema PR also lands:

- New valid examples: `examples/valid/runtime_snapshot_1_3.json` (full 5-axis), `examples/valid/digital_only.json` (browser/desktop producer with no biosensor or motion), `examples/valid/categorical_kinematic.json`, `examples/valid/multimodal_cognitive.json`, `examples/valid/affective_digital_only_research.json` (digital-only `valence` reading from a research producer — illustrates the §9 SHOULD vs. MUST decision: the affective-availability rule is a producer-policy SHOULD in 1.3, so this payload validates).
- New invalid examples: `examples/invalid/missing_modality.json`, `examples/invalid/categorical_score_conflict.json`, `examples/invalid/multimodal_without_modalities_used.json`.
- Strict validator path `tests/hsi_validate.py::_validate_strict_13` and `test-vectors/v1.3/` regression fixtures.
- CHANGELOG `[1.3]` entry covering this RFC, RFC-HSI-0009, and any other 1.3-targeted changes.
- README badge bump to 1.3 with links to RFC-HSI-0010 and RFC-HSI-0011 (when published).
