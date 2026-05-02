# RFC-HSI-0011

## HSI 1.3 — Per-Modality Signal Fidelity Tiers

- **Status**: Draft
- **Type**: Minor (breaking under pre-stable; replaces `source_tier` with `tiers` in 1.3)
- **Target**: HSI 1.3
- **Owner**: HSI Maintainers
- **Paired with**: RFC-HSI-0010 (5-axis domain set and modality model). 0010 + 0011 are a single 1.3 change; both MUST be Accepted before the 1.3 schema PR proceeds. The modality keys this RFC uses (`physiological`, `kinematic`, `digital`) are defined by RFC-HSI-0010 §6.
- **Depends on**: PR #5 against `synheart-ai/hsi` (1.2 source descriptors). The per-source tier placement in §6.2 sits alongside PR #5's source-level fields. PR #5 MUST land before the 1.3 schema PR.
- **Relates to**: RFC-HSI-0008 (HSI 1.2 canonical contract; defines `source_tier`), RFC-HSI-0009 (HSI 1.3 integrity block, independent)
- **Canonical schema**: `schema/hsi-1.3.schema.json` (added when this RFC and RFC-HSI-0010 are Accepted)

## 1. Purpose

HSI 1.2 (RFC-HSI-0008 §6.7) defines a single integer field, `source_tier` (1–4), to describe the fidelity of evidence backing a reading or embedding. Despite the generic name, the four tiers and the table that documents them are **physiology-specific**: they describe a degradation ladder from native RR intervals (Tier 1) to a single HR snapshot (Tier 4). The field cannot honestly describe the fidelity of a kinematic or digital-interaction signal, and it implicitly forces those modalities to share one ladder with physiology even though they are independent observation channels.

RFC-HSI-0010 makes the modality structure explicit (`physiological`, `kinematic`, `digital`, `multimodal`). This RFC follows that structure into the fidelity-tier model. HSI 1.3 introduces a **`tiers` object** carrying one optional fidelity tier per observable modality:

```json
"tiers": {
  "physiological": 2,
  "kinematic":     1,
  "digital": 1
}
```

In HSI 1.3, `tiers` **replaces** `source_tier`. The 1.3 schema does not accept `source_tier` at any of the three sites it appeared in 1.2 (`axis_reading`, `embedding`, `meta.provenance.sources[*]`); 1.3 producers MUST emit `tiers` instead. This is a breaking change permitted under HSI's pre-stable regime (`versioning.md`). 1.2 payloads continue to validate against `schema/hsi-1.2.schema.json` unchanged.

The motivating consumer cases:

- **Multimodal heads need per-channel attribution.** A `cognitive.focus` reading derived from HRV (`physiological` Tier 2) plus rich phone interaction (`digital` Tier 1) is not the same as one derived from a single HR snapshot (`physiological` Tier 4) plus sparse interaction (`digital` Tier 3). The current single integer cannot distinguish these cases; the new object can.
- **Digital-only producers need an honest tier.** Producers without any biosensor — desktop agents, browser extensions, mobile apps without a paired wearable — have no physiological signal at all. Forcing `source_tier: 4` to mean "no biosignal" conflates "single HR snapshot" with "no HR data," which are different evidence states with different confidence semantics. The new model lets such producers omit `tiers.physiological` entirely and declare `tiers.digital` (and/or `tiers.kinematic`) honestly.
- **Confidence caps need per-modality grounding.** Today consumers cap probabilistic-model confidence at the physiological tier (e.g. probabilistic models refuse to run when `source_tier >= 3`). With multimodal inference, the cap should depend on which modalities contributed and at what fidelity each. Per-modality tiers make that policy expressible.

## 2. Non-goals

- **Modality definition.** RFC-HSI-0010 §6 defines the four canonical modalities. This RFC takes that set as given.
- **Axis-domain redesign.** RFC-HSI-0010 §4 defines the 5-axis canonical domain set. This RFC takes that set as given.
- **Calibration of confidence priors.** Per-modality confidence caps in §5 are starting priors derived from product judgment, not from validation against a labeled dataset. Producers and consumers SHOULD treat the numeric caps as initial recommendations subject to revision once a calibration study is published. The cap *structure* (per-modality, monotonically decreasing with tier) is normative; the *exact values* are open until calibration.
- **Per-source vs per-reading semantics.** `tiers` follows the placement and resolution rules from RFC-HSI-0008 §6.7 (authoritative at source, overridable per reading). This RFC restates them in §6.3 for completeness but does not change them.

## 3. Relation to prior RFCs

- **RFC-HSI-0008** §6.7 defines `source_tier` (integer 1–4) on `axis_reading`, `embedding`, and (post-PR #5) `meta.provenance.sources[*]`. In HSI 1.3 this RFC removes `source_tier` from those three sites and replaces it with `tiers`. The 1.2 tier table (§6.7) is preserved as the definition of `tiers.physiological`.
- **RFC-HSI-0010** introduces `modality` and `modalities_used` on every axis_reading. The keys of `tiers` correspond exactly to RFC-HSI-0010's three observable modalities (`physiological`, `kinematic`, `digital`); the fourth modality `multimodal` is a fusion outcome and has no tier of its own.
- **RFC-HSI-0009** is independent. Both this RFC and RFC-HSI-0009 land in `schema/hsi-1.3.schema.json`.

## 4. Per-modality fidelity ladders

Each observable modality has its own fidelity ladder. Lower tier numbers indicate higher fidelity, matching the existing `source_tier` convention (RFC-HSI-0008 §6.7).

### 4.1 `physiological` tiers

Carried over unchanged from RFC-HSI-0008 §6.7. `tiers.physiological` MUST be one of:

| Tier | Evidence class | Typical examples |
|---|---|---|
| 1 | Ground truth | Beat-to-beat RR intervals, lab-grade ECG, raw PPG with on-device beat detection |
| 2 | Vendor-derived high-fidelity | Calibrated HRV metrics from a vendor SDK, vendor-fused biosignal features |
| 3 | Proxy time series | Coarse-rate (≤1 Hz) HR traces, motion-derived HR proxies — trends preserved, variability lost |
| 4 | Snapshot / minimal | Single spot HR values, low-resolution checks |

### 4.2 `kinematic` tiers

`tiers.kinematic` MUST be one of:

| Tier | Evidence class | Typical examples |
|---|---|---|
| 1 | High-rate inertial | Continuous accelerometer ≥50 Hz; multi-axis with gyroscope or magnetometer |
| 2 | Event-based / coarse | Step events, low-rate accelerometer (<25 Hz), motion-state transitions |
| 3 | Sparse / vendor-aggregate | Hourly activity bins, daily step totals, vendor-classified activity labels with no underlying time series |

Producers that have no kinematic signal at all MUST omit `tiers.kinematic` rather than emit a sentinel value.

### 4.3 `digital` tiers

`tiers.digital` MUST be one of:

| Tier | Evidence class | Typical examples |
|---|---|---|
| 1 | Rich | Multi-kind events (taps, scrolls, app switches, typing) sustained over a long window (≥120 s) at ≥30 events/min |
| 2 | Moderate | Single- or dual-kind events sustained over a full session window (≥60 s) at ≥10 events/min |
| 3 | Sparse | Brief windows (<60 s) or low event density (<10 events/min); directional signal only |

Producers with no digital-interaction signal MUST omit `tiers.digital`.

The thresholds in §4.3 are operational defaults derived from typical mobile and desktop session telemetry. Producers MAY adopt domain-specific thresholds and document them in `meta.provenance` (`engine`, `engine_version`); consumers comparing readings across producers SHOULD verify thresholds match before treating tiers as equivalent.

## 5. Confidence caps per tier

Producers and consumers MAY cap reported `confidence` based on the most-conservative tier among the modalities that contributed to a reading. The cap structure is normative; the exact numeric values are starting priors subject to calibration (§2).

| Modality | Tier 1 cap | Tier 2 cap | Tier 3 cap | Tier 4 cap |
|---|---|---|---|---|
| `physiological` | 1.0 | 0.9 | 0.7 | 0.5 |
| `kinematic` | 0.85 | 0.65 | 0.40 | — |
| `digital` | 0.85 | 0.65 | 0.40 | — |

For multimodal readings, the cap is computed per modality from the contributing tiers and combined per producer policy. A common policy is `cap = max(per_modality_caps)` — the best contributing channel sets the ceiling — but other policies (weighted-mean, min-of-required) are permissible. Producers SHOULD document their cap policy in `meta.provenance.engine_version` documentation.

The caps replace the implicit "Tier ≥ 3 forbids probabilistic models" heuristic from RFC-HSI-0008 §6.7. That heuristic remains valid for `tiers.physiological` consumers; per-modality equivalents are producer-defined.

## 6. The `tiers` object

### 6.1 Shape

```json
"tiers": {
  "physiological":      <integer 1..=4>,
  "kinematic":          <integer 1..=3>,
  "digital": <integer 1..=3>
}
```

- `additionalProperties: false`. Adding a new tier key requires a new RFC and a schema bump.
- `minProperties: 1`. An empty `tiers` object MUST NOT be emitted; producers either include the object with at least one populated tier or omit the field entirely.
- Each property is optional; absence MUST be interpreted as "this modality did not contribute to this reading," **not** as zero or as the highest-numbered tier. Consumers MUST distinguish absence from a present low tier.

### 6.2 Where it lives

`tiers` is permitted at the same three sites as `source_tier`:

- **`meta.provenance.sources[*].tiers`** — authoritative tier set for the source. Inherited by readings and embeddings that cite the source via `evidence_source_ids`. Exactly one tier key SHOULD be populated per source unless the source genuinely produces multiple modalities (rare but valid: a phone that emits both `kinematic` and `digital`).
- **`axis_reading.tiers`** — per-reading override or declaration. Required semantics match `source_tier` (RFC-HSI-0008 §6.7): the per-reading value overrides inherited source-level tiers when present; producers SHOULD use overrides only to *demote* (cite a higher-numbered tier than the source declares), not to promote.
- **`embedding.tiers`** — per-embedding tier set. Mirrors `axis_reading.tiers` semantics.

### 6.3 Resolution precedence

For a single reading or embedding, the effective per-modality tier is:

1. Per-reading / per-embedding `tiers.<modality>` if set.
2. Otherwise, the worst-numbered (highest-integer) value among `tiers.<modality>` declared on cited sources via `evidence_source_ids`.
3. Otherwise, unknown.

The "worst-numbered wins" rule mirrors RFC-HSI-0008 §6.7 and is conservative: when multiple sources of the same modality contribute, the reading inherits the most-degraded fidelity.

## 7. Replacement of `source_tier`

In HSI 1.3, `source_tier` is removed at all three sites it appeared in 1.2 (`axis_reading`, `embedding`, `meta.provenance.sources[*]`). 1.3 schemas reject the field via `additionalProperties: false`. Producers MUST emit `tiers` instead.

This is a clean break, not a deprecation. HSI is pre-stable (`versioning.md`); minor versions MAY introduce breaking contract changes until 2.0. Sustaining a dual-emit window across `source_tier` and `tiers` would require validator-enforced cross-field consistency rules and lasting producer/consumer ambiguity for no compensating benefit, given that producers and consumers already coordinate per `hsi_version` (RFC-HSI-0008 §12).

### 7.1 Producer obligations

- 1.3 producers MUST emit `tiers` wherever they previously emitted `source_tier`. The 1.2 → 1.3 mapping is `source_tier: N` → `tiers: { "physiological": N }`.
- Producers SHOULD additionally populate `tiers.kinematic` and `tiers.digital` from their modality availability. Omit modality keys for which there is no signal.
- 1.3 producers MUST NOT emit `source_tier`. The schema rejects it.

### 7.2 Consumer obligations

- 1.3 consumers read `tiers`. `source_tier` does not appear in 1.3 payloads; consumers SHOULD NOT look for it.
- Consumers that ingest both 1.2 and 1.3 traffic dispatch on `hsi_version` (RFC-HSI-0008 §12) and validate against the schema for the declared version. The 1.2 path continues to read `source_tier`; the 1.3 path reads `tiers`.

## 8. Schema additions

This section enumerates the concrete `schema/hsi-1.3.schema.json` changes for the tier model relative to `schema/hsi-1.2.schema.json`. Materialized in the schema PR that lands when this RFC and RFC-HSI-0010 are Accepted.

### 8.1 `$defs` additions

```json
"physio_tier_value": {
  "type": "integer",
  "minimum": 1,
  "maximum": 4
},

"kinematic_tier_value": {
  "type": "integer",
  "minimum": 1,
  "maximum": 3
},

"digital_tier_value": {
  "type": "integer",
  "minimum": 1,
  "maximum": 3
},

"tiers": {
  "type": "object",
  "additionalProperties": false,
  "minProperties": 1,
  "properties": {
    "physiological":       { "$ref": "#/$defs/physio_tier_value" },
    "kinematic":           { "$ref": "#/$defs/kinematic_tier_value" },
    "digital": { "$ref": "#/$defs/digital_tier_value" }
  }
}
```

The 1.2 `$defs/source_tier` definition is **removed** in 1.3. References to it from `axis_reading`, `embedding`, and `meta.provenance.sources[*]` are removed at the same time.

### 8.2 Field additions

Added at three sites — identical shape, identical semantics:

- `axis_reading.tiers` (optional): `{ "$ref": "#/$defs/tiers" }`.
- `embedding.tiers` (optional): `{ "$ref": "#/$defs/tiers" }`.
- `meta.provenance.sources[*].tiers` (optional): `{ "$ref": "#/$defs/tiers" }`.

### 8.3 Field removals

Removed at the same three sites:

- `axis_reading.source_tier`
- `embedding.source_tier`
- `meta.provenance.sources[*].source_tier`

The 1.3 schema's `additionalProperties: false` on each container rejects payloads that include `source_tier`. The 1.2 schema (`schema/hsi-1.2.schema.json`) is unchanged; 1.2 payloads continue to validate against it.

## 9. Compliance

- **HSI-VALIDATE-BASIC**: validates `tiers` object structure, key set, and value ranges per `schema/hsi-1.3.schema.json`. Rejects `source_tier` at any of the three former sites.
- **HSI-VALIDATE-STRICT**: BASIC plus the following checks in `tests/hsi_validate.py::_validate_strict_13`:
  - All RFC-HSI-0008 §10 STRICT checks remain (those that do not depend on `source_tier`).
  - All RFC-HSI-0010 §12 STRICT checks remain.
  - **`tiers` non-empty**: when the field is present, it MUST contain ≥1 populated key. (`minProperties: 1` in §8.1 enforces this at BASIC; STRICT re-checks for defense in depth.)
  - **Tier-domain consistency** (informational warning, not failure): when an axis_reading appears in one of the three single-modality domains (`axes.physiological[]`, `axes.kinematic[]`, `axes.digital[]`) and `tiers` is present, `tiers.<domain>` SHOULD also be present. Producers emitting a single-modality reading without a tier for that modality lose the ability to express fidelity; STRICT emits a warning (HSI-1.3-TIERS-MISSING-FOR-MODALITY) but does not reject. (Per RFC-HSI-0010 §5.2, modality on single-modality readings is encoded by the axis domain key, not by a separate `modality` field.)

## 10. Migration from HSI 1.2

The 1.2 → 1.3 migration is a single rename plus optional enrichment.

Producers:

1. **Rename** every `source_tier: N` (on a source, axis_reading, or embedding) to `tiers: { "physiological": N }` at the same site.
2. **Enrich** by populating `tiers.kinematic` and `tiers.digital` per the producer's modality availability. Omit modality keys for which the producer has no signal.
3. **Set** `hsi_version: "1.3"`.

Consumers:

1. Read `tiers` from 1.3 payloads.
2. Continue reading `source_tier` from 1.2 payloads validated against `schema/hsi-1.2.schema.json`.
3. **Treat absence** of a modality key as "no signal," not as the highest-numbered tier. Specifically: a behavior-only producer omits `tiers.physiological`; consumers MUST NOT interpret that absence as "Tier 4 physiology."

Producers and consumers SHOULD migrate together on a per-`hsi_version` basis (RFC-HSI-0008 §12). Producers that need to serve 1.2-only consumers continue to emit 1.2 payloads with `source_tier`; the 1.2 schema is unchanged.

## 11. Privacy considerations

- `tiers` carries fidelity metadata, not behavioral content. It does not weaken `privacy.contains_pii: false` (RFC-HSI-0008 §9).
- `tiers.kinematic` and `tiers.digital` indirectly reveal that the producer has motion or interaction telemetry available. This is operationally already implied by per-source `signals` (RFC-HSI-0008 §7, PR #5) and by which axis domains the producer emits, so the fidelity declaration adds no new fingerprinting surface beyond what those fields already expose.
- Per-source `vendor` warnings from RFC-HSI-0008 §7 still apply when `tiers` is co-located with `vendor` on a source descriptor.

## 12. Open questions

Before promoting this RFC to Accepted:

- **Confidence-cap calibration.** The values in §5 are starting priors. A validation study comparing behavior-only and kinematic-led inference against a physiological reference (HRV-derived focus, e.g. on N≥30 dual-record sessions) is needed to set defensible caps. Should this RFC ship with the priors marked normative, advisory, or omit the table entirely until calibration?
- **Tier-direction polarity.** This RFC keeps the "lower number = higher fidelity" convention inherited from RFC-HSI-0008 §6.7 for continuity with the 1.2 tier table. An alternative ("higher number = higher fidelity," matching the intuitive "more is better" convention used in `score`) is more readable for new consumers. Lock in lower-is-better for 1.3, or invert?
- **Multi-modality-per-source.** Some sources (a phone) genuinely produce multiple modalities. Current draft permits multiple `tiers.<modality>` keys on a single source descriptor. Alternative: require one tier key per source, forcing producers to declare separate logical sources for `phone-os-events` and `phone-accel`. Single-source-multi-tier is more compact; split-sources is cleaner attribution.
- **Per-modality cap policy.** §5 states the cap structure is normative and fusion policy is producer-defined. Should this RFC also normatively define a default fusion policy (e.g. "cap = max of contributing modality caps") to avoid silent producer drift?

## 13. Canonical schema

When this RFC is Accepted alongside RFC-HSI-0010, the changes in §8 are materialized in `schema/hsi-1.3.schema.json`. `schema/hsi-1.2.schema.json` is unchanged.

The schema PR also lands:

- New valid examples: `examples/valid/tiers_multimodal.json` (axis_reading with all three tier keys populated and a multimodal cognitive reading), `examples/valid/tiers_digital_only.json` (digital-only producer, `tiers.physiological` absent).
- New invalid examples: `examples/invalid/tiers_source_tier_present.json` (`source_tier` field present in a 1.3 payload), `examples/invalid/tiers_empty_object.json` (`tiers: {}`), `examples/invalid/tiers_unknown_modality.json` (`tiers.audio: 1`).
- Strict validator warning code `HSI-1.3-TIERS-MISSING-FOR-MODALITY` in `tests/hsi_validate.py::_validate_strict_13`.
- CHANGELOG `[1.3]` entry covering this RFC together with RFC-HSI-0010 and RFC-HSI-0009.
- README badge bump to 1.3 with links to RFC-HSI-0010 and RFC-HSI-0011.
