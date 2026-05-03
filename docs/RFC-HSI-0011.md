# RFC-HSI-0011

## HSI 1.3 — Per-Channel Confidence Breakdown on Multimodal Readings

- **Status**: Draft (revised; supersedes the earlier per-modality `tiers` design)
- **Type**: Minor (additive)
- **Target**: HSI 1.3
- **Owner**: HSI Maintainers
- **Paired with**: RFC-HSI-0010 (5-axis canonical domain set and modality model). The observable modalities this RFC uses (`physiological`, `kinematic`, `digital`) are defined by RFC-HSI-0010 §6.
- **Depends on**: PR #5 against `synheart-ai/hsi` (1.2 source descriptors). PR #5 MUST land before the 1.3 schema PR.
- **Relates to**: RFC-HSI-0008 (HSI 1.2 canonical contract), RFC-HSI-0009 (HSI 1.3 integrity block, independent)
- **Canonical schema**: `schema/hsi-1.3.schema.json` (added when this RFC and RFC-HSI-0010 are Accepted)

## 1. Purpose

Multimodal axis readings (`axes.cognitive[*]`, `axes.affective[*]`) fuse evidence from more than one observation channel. A consumer reading `cognitive.focus = 0.74, confidence = 0.82` knows the producer's overall certainty, but cannot tell how that certainty broke down across the contributing channels — the same `confidence` could come from rich physiological + sparse digital, or from sparse physiological + rich digital, with very different downstream trust implications.

HSI 1.3 introduces an optional **`confidence_breakdown`** field on multimodal axis readings. It maps each contributing observable modality (`physiological`, `kinematic`, `digital`) to a per-channel confidence in `[0, 1]`:

```json
{
  "name": "focus",
  "score": 0.74,
  "confidence": 0.82,
  "modalities_used": ["physiological", "digital"],
  "confidence_breakdown": {
    "physiological": 0.85,
    "digital": 0.78
  }
}
```

`confidence_breakdown` is **additive on top of the carried-over `source.source_tier` field** (RFC-HSI-0008 §6.7, unchanged from HSI 1.2 post-PR #5). The two solve different problems: `source.source_tier` describes *architectural* fidelity of an input channel ("Tier 1 = ground-truth RR intervals; Tier 4 = single HR snapshot") and lives on the source descriptor; `confidence_breakdown` describes *per-channel inference confidence on a fused multimodal reading* and lives inline on the reading. A reading can — and typically does — have both:

- The source-level `source_tier` tells consumers what fidelity ceiling the input channel can ever hit.
- The reading-level `confidence_breakdown` tells consumers how confident the producer was in each channel's contribution to *this specific multimodal output*.

An earlier draft of this RFC introduced a per-modality `tiers` object on `meta.provenance.sources[*]` (with keys `physiological` / `kinematic` / `digital`) plus a normative cap table tying each tier value to a downstream confidence ceiling. That design was rejected during 1.3 review:

- **The cap table shipped uncalibrated values** as normative starting priors. Once consumers coded against `tiers.physiological: 4 → cap: 0.5`, recalibration would be breaking; HSI is pre-stable, but the cap surface was load-bearing infrastructure that didn't yet have data behind it.
- **The `kinematic` and `digital` ladders were invented** — sample-rate and event-density thresholds admittedly derived from "operational defaults," not from a calibration result.
- **The per-modality split forced producers** with single-purpose sources to think about modalities they didn't have, and forced producers with cross-modal sources (a phone emitting both `kinematic` and `digital`) to fill in multiple tier values.
- **The 1.2 → 1.3 migration had a silent semantic gotcha**: a 1.2 producer using `source_tier: 4` to mean "no biosignal" would, under naive rename, become `tiers: { physiological: 4 }` ("minimal biosignal") — a different meaning.

The carried-over `source.source_tier` integer (1.2 shape) avoids all five problems: no cap table, single integer (no per-modality split), no migration gotcha (the field name and shape are unchanged), and no resolution-function complexity beyond what 1.2 already had. `confidence_breakdown` then handles the orthogonal use case — per-channel attribution on multimodal readings — directly on the reading itself, without rebuilding source-level infrastructure.

## 2. Non-goals

- **Redesigning `source.source_tier`.** The 1.2 (post-PR #5) `source.source_tier` integer (1–4) is carried over to 1.3 unchanged in name, shape, and meaning. RFC-HSI-0008 §6.7 remains its authoritative definition. This RFC neither redefines it nor introduces a per-modality replacement; the per-modality `tiers` object explored in an earlier draft was rejected (§1).
- **A normative fusion policy.** Producers that emit `confidence_breakdown` are expressing how they decomposed their fused confidence; this RFC does not specify how the breakdown components are combined into the overall `confidence` value. That is a producer-internal decision documented in `meta.provenance.engine_version`.
- **Single-modality readings.** Readings in `axes.physiological[]`, `axes.kinematic[]`, `axes.digital[]` do not carry `confidence_breakdown` — there is only one contributing modality and the parent domain key already encodes it. The schema rejects `confidence_breakdown` on single-modality readings.

## 3. Relation to prior RFCs

- **RFC-HSI-0008** §6.7 (post-PR #5) defines `source_tier` (integer 1–4) on `meta.provenance.sources[*]`. **HSI 1.3 carries that field over unchanged** — same name, same shape, same physiology-flavored tier table. RFC-HSI-0008 §6.7 remains the authoritative definition. The earlier idea of replacing `source_tier` with a per-modality `tiers` object was rejected (§1) and is not part of 1.3.
- **RFC-HSI-0010** introduces the 5-axis canonical domain set and `modalities_used` on multimodal axis_readings. The keys of `confidence_breakdown` are exactly the three observable modalities defined in RFC-HSI-0010 §6 (`physiological`, `kinematic`, `digital`); the fourth canonical modality `multimodal` is a fusion outcome and has no breakdown of its own.
- **RFC-HSI-0009** is independent. Both this RFC and RFC-HSI-0009 land in `schema/hsi-1.3.schema.json`.

## 4. The `confidence_breakdown` field

### 4.1 Shape

```json
"confidence_breakdown": {
  "type": "object",
  "additionalProperties": false,
  "minProperties": 1,
  "properties": {
    "physiological": { "$ref": "#/$defs/score01" },
    "kinematic":     { "$ref": "#/$defs/score01" },
    "digital":       { "$ref": "#/$defs/score01" }
  }
}
```

- `additionalProperties: false`: only the three observable modalities are valid keys.
- `minProperties: 1`: an empty `confidence_breakdown` MUST NOT be emitted; producers that have nothing to say about per-channel confidence omit the field entirely.
- Each property is optional and is a `[0, 1]` score with the same semantics as `confidence`: the producer's certainty in the contribution from that channel to the reading. Absence MUST be interpreted as "the producer did not attribute confidence to this channel," not as zero.

### 4.2 Where it lives

`confidence_breakdown` is permitted **only** on readings in the multimodal axis domains (`axes.cognitive[*]`, `axes.affective[*]`). It is rejected on readings in single-modality domains (`axes.physiological[*]`, `axes.kinematic[*]`, `axes.digital[*]`) — the parent domain key already encodes the only contributing channel, and a per-channel breakdown over a single channel is redundant. Schema-level enforcement is via the `axes_domain_single_modality` wrapper (`not: { required: [confidence_breakdown] }`).

### 4.3 Relationship to `modalities_used` and `confidence`

The keys of `confidence_breakdown` SHOULD be a subset of `modalities_used` on the same reading: a producer that lists `modalities_used: ["physiological", "digital"]` and then attributes confidence to `kinematic` is internally inconsistent. HSI-VALIDATE-STRICT enforces this as `HSI-1.3-CONFIDENCE-BREAKDOWN-MISMATCH`.

The relationship between `confidence_breakdown` values and the overall reading `confidence` is producer-defined. Common policies:

- **Max policy:** `confidence = max(confidence_breakdown.values())` — the strongest contributing channel sets the ceiling.
- **Mean policy:** `confidence = mean(confidence_breakdown.values())` — flat average across cited channels.
- **Weighted policy:** producer documents per-channel weights elsewhere (typically tied to a model artifact referenced by `model_id`).

This RFC does not pick one. Producers SHOULD document their fusion policy out of band (e.g. in the artifact at `model_id`, or in the engine documentation referenced via `meta.provenance.engine_version`). Consumers MAY compute their own derived signal from `confidence_breakdown` (e.g. "trust this reading only if all contributing channels are above 0.6") without needing the producer's fusion policy.

## 5. Schema additions

### 5.1 `$defs` additions

No new `$defs`. `confidence_breakdown` is a small inline object on `axis_reading` and the per-key value type is the existing `$defs/score01`.

### 5.2 Field additions

Added at one site:

- `axis_reading.confidence_breakdown` (optional): inline object as defined in §4.1.

Schema-level placement (multimodal-only) is enforced via `axes_domain_single_modality` and `axes_domain_multimodal` wrappers, the same construct that handles `modalities_used`.

### 5.3 Field removals

None at the source level. `meta.provenance.sources[*].source_tier` and `$defs/source_tier` are carried over from HSI 1.2 (post-PR #5) unchanged.

The 1.2 schema (`schema/hsi-1.2.schema.json`) is unchanged; 1.2 payloads continue to validate against it.

## 6. Compliance

- **HSI-VALIDATE-BASIC**: validates `confidence_breakdown` shape and key set against `schema/hsi-1.3.schema.json`. Rejects `confidence_breakdown` on a single-modality reading (via `axes_domain_single_modality`'s `not: { required: [confidence_breakdown] }`). The `source.source_tier` field is validated as integer in 1..=4 via `$defs/source_tier` (carried over from 1.2).
- **HSI-VALIDATE-STRICT**: BASIC plus the following checks in `tests/hsi_validate.py::_validate_strict_13`:
  - All RFC-HSI-0008 §10 STRICT checks remain (including the `source_tier` range check via schema-level `$defs/source_tier`).
  - All RFC-HSI-0010 §12 STRICT checks remain.
  - **`HSI-1.3-CONFIDENCE-BREAKDOWN-FORBIDDEN`**: a reading in `axes.physiological[]`, `axes.kinematic[]`, or `axes.digital[]` MUST NOT include `confidence_breakdown` (defense in depth; primary enforcement is at BASIC).
  - **`HSI-1.3-CONFIDENCE-BREAKDOWN-MISMATCH`**: when both `modalities_used` and `confidence_breakdown` are present, every key of `confidence_breakdown` MUST appear in `modalities_used`. The reverse subset is not enforced — producers may list `modalities_used` channels for which they don't separately attribute confidence (e.g. a channel that contributed but at uniform weight).
  - **Defensive rejection of the per-modality `tiers` object** on any source (the rejected design from §1). STRICT raises a clear error pointing producers at the carried-over `source.source_tier` integer and the additive `axis_reading.confidence_breakdown` field.

## 7. Migration from HSI 1.2

Migration on the source-tier surface is **zero-effort** — `source.source_tier` carries over unchanged. The only 1.3 addition that this RFC contributes is the optional `axis_reading.confidence_breakdown` field on multimodal readings.

Producers:

1. **Keep** `source.source_tier` on every applicable entry in `meta.provenance.sources` exactly as in 1.2. Tier values, semantics, and the physiology-flavored §6.7 ladder are unchanged.
2. **Adopt** `confidence_breakdown` on multimodal readings (`axes.cognitive[*]`, `axes.affective[*]`) where the producer has per-channel confidence to attribute. Optional; producers without a meaningful per-channel breakdown omit the field.
3. **Set** `hsi_version: "1.3"`.

Consumers:

1. Continue reading `source.source_tier` from both 1.2 and 1.3 payloads — same field, same semantics.
2. On 1.3 payloads, additionally read `axis_reading.confidence_breakdown` (if present) for per-channel attribution on multimodal readings.

Producers and consumers SHOULD migrate together on a per-`hsi_version` basis (RFC-HSI-0008 §12).

## 8. Privacy considerations

- `confidence_breakdown` is metadata about the producer's inference, not behavioral content. It does not weaken `privacy.contains_pii: false`.
- Per-channel confidence does not identify the user any more than the overall `confidence` already does.
- Per-source `vendor` warnings from RFC-HSI-0008 §7 still apply to the 1.3 source descriptor; this RFC does not change them.

## 9. Provisional status and 1.4 revisit

`confidence_breakdown` ships in 1.3 at **SHOULD strength**: producers MAY emit it; consumers MAY read it. Whether the field stays in 1.4 unchanged, gets promoted to a normative MUST on multimodal readings, or gets removed entirely depends on real-world adoption between 1.3 and 1.4. Two questions to watch:

- **Producer adoption.** A producer using a learned multimodal model often *cannot* produce a meaningful per-channel breakdown (the model's internal weights aren't channel-separable). A producer using a rulepack with explicit per-channel weighting can. If most 1.3 producers are in the first camp, `confidence_breakdown` ends up sparsely populated and consumers can't rely on it.
- **Consumer demand.** Without a calibrated per-channel cap policy (deliberately deferred — see RFC-HSI-0011 §1's rejection of the original `tiers` cap table), consumers have no normative use for the breakdown values. If no real consumer reads them within the 1.3 → 1.4 window, the field is dead surface.

**1.4 revisit decision rule:** if at least one canonical producer (synheart-flux or another) populates `confidence_breakdown` consistently and at least one canonical consumer reads it for a real downstream policy, keep the field. Otherwise, deprecate in 1.4 and remove in 1.5.

## 10. Open questions

Before promoting this RFC to Accepted:

- **Subset rule strictness.** §4.3 / §6 enforce `confidence_breakdown.keys() ⊆ modalities_used`. Should the reverse also be required (every `modalities_used` channel MUST appear in `confidence_breakdown`)? Current draft permits a producer to list a channel in `modalities_used` without separately attributing confidence to it (the channel contributed but without a numeric breakdown). Stricter rule simplifies consumer parsing; current rule is more honest about producer capability.
- **Future categorical tiers.** §2 defers categorical fidelity tiers to a future RFC pending calibration data. Should we reserve a `tiers` key on `meta.provenance.sources[*]` now (as a no-value-yet placeholder) to ease the future addition, or leave the source descriptor clean and accept that adding `tiers` later will be a minor schema change?

## 11. Canonical schema

When this RFC is Accepted alongside RFC-HSI-0010, the changes in §5 are materialized in `schema/hsi-1.3.schema.json`. `schema/hsi-1.2.schema.json` is unchanged.

The schema PR also lands:

- New valid example: `examples/valid/confidence_breakdown.json` (multimodal cognitive reading with breakdown across `physiological` + `digital`). The full-payload example `examples/valid/runtime_snapshot_1_3.json` and `examples/valid/multimodal_cognitive.json` are updated to demonstrate the field.
- New invalid examples: `examples/invalid/confidence_breakdown_on_single_modality.json` (`confidence_breakdown` on a `physiological[*]` reading), `examples/invalid/confidence_breakdown_unknown_modality.json` (key not in the observable-modality set), `examples/invalid/confidence_breakdown_mismatch.json` (key not in `modalities_used`), `examples/invalid/source_tiers_object_in_1_3.json` (the rejected per-modality `tiers` object on a 1.3 source).
- Strict validator codes `HSI-1.3-CONFIDENCE-BREAKDOWN-FORBIDDEN` and `HSI-1.3-CONFIDENCE-BREAKDOWN-MISMATCH` in `tests/hsi_validate.py::_validate_strict_13`.
- CHANGELOG `[1.3]` entry covering this RFC together with RFC-HSI-0010 and RFC-HSI-0009.
- README badge bump to 1.3 with links to RFC-HSI-0010 and RFC-HSI-0011.
